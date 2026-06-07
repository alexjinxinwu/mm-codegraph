## Design Summary

在 `codegraph_core` 中新增图模型内核：两张静态注册表（NodeSpec、EDGE_RULES）描述 14 种 ER 节点与 19 条 forward(out) 边，以及一个 `build_expand_query(rule, node, limit)` 生成器，把「一条边 + 一个起点节点」翻译成参数化 SELECT。节点身份（自增 id）与表间关联（业务列 match）严格分离；边分平凡、语义、guard 三类，语义边显式标注数据假设，guard 边支持逗号分隔列表拆分。本能力为纯内核逻辑，不暴露 HTTP，可与上层 `/resolve`、`/expand` 及 MCP 工具并行集成。

## Alternatives Considered

### Alternative A: 声明式双注册表 + SQL 生成器（NodeSpec + EDGE_RULES）

- **Approach**: 用 Python dict/dataclass 静态注册 14 种 NodeSpec 与 19 条 EdgeRule；`build_expand_query` 读取 rule.match 与 node 字段值，生成带绑定参数的 SELECT … WHERE … LIMIT。
- **Pros**:
  - 与 ER 真源（`codegraph_mcp/ER.md`）一一对应，新增边类型只改一处
  - 列异名、复合键、guard 拆分均可通过 match/guard 字段表达，无需为每种边写独立函数
  - 上层 `/expand` 与 MCP 共用同一内核，行为一致
  - 加载时校验（类型存在、id 唯一、guard 必填）可在启动阶段 fail-fast
- **Cons**:
  - 规则表需手工维护，schema 变更时要同步更新
  - 语义边假设（logic 列存 chain_id）无法在编译期验证，需后续数据校验 change
- **Why chosen**: 与 proposal/spec 一致，覆盖全部 19 条 forward 边且可测试；比散落 SQL 更可维护，比 ORM 反射更轻量、与现有 PyMySQL 栈契合

### Alternative B: 数据库元数据反射（information_schema 驱动）

- **Approach**: 启动时从 MySQL `information_schema` 读取表/列/外键，自动推断节点与边；SQL 生成器基于推断结果动态拼装。
- **Pros**:
  - schema 变更时理论上可自动感知
  - 减少手工维护注册表
- **Cons**:
  - 真实 ER 关系大量建立在业务列上且列名异名（bean_class→full_qualified_name），information_schema 无外键可反射
  - 语义边与 guard 边（逗号拆分）无法从元数据推断，仍需额外规则层
  - 引入运行时依赖与启动延迟，与当前「静态 14 表、关系已知」场景不匹配
- **Why not chosen**: 反射无法表达列异名、复合键、guard 变换；最终仍要回到声明式规则，复杂度更高收益更低

### Alternative C: 按边上 scattered 手写 SQL（MCP 工具内嵌）

- **Approach**: 在 MCP server 或 HTTP handler 中为每种 from→to 关系写独立 SQL 片段，调用方按 nodeType 分支选择。
- **Pros**:
  - 实现最快，无需抽象层
  - 每条 SQL 可读性直观
- **Cons**:
  - 19 条边 × 多 transport（MCP + HTTP）= 重复与行为漂移风险
  - 列异名、guard IN、LIMIT、参数绑定等横切逻辑散落各处
  - 无法统一校验规则完整性（主路线连通性、类型引用）
- **Why not chosen**: 与 refactor 后「QueryEngine 为单一真源」架构方向冲突；维护成本随边数量线性增长

## Agreed Approach

**Alternative A: 声明式双注册表 + SQL 生成器**

在 `codegraph_core` 新增 `graph/` 子模块，包含：

1. **node_specs.py** — 14 种 NodeSpec 静态注册表 + 按 nodeType 查找 + 加载校验
2. **edge_rules.py** — 19 条 forward EdgeRule（14 单列 + 2 复合 + 2 语义 + 1 guard）+ 按 from 筛选 + 加载校验
3. **expand_query.py** — `build_expand_query(rule, node, limit)` 返回 `(sql, params)` 元组

与现有 `QueryEngine.q(schema, sql, params)` 对接：上层传入 schema 与生成结果即可执行，无需修改 QueryEngine 本身。

## Key Decisions

1. **模块落点**: 新代码放在 `codegraph_core/graph/`，与 `query_engine.py`、`models.py` 同级；TypedDict 实体模型保留在 `models.py`，NodeSpec/EdgeRule 为图元数据，不混用。
2. **NodeSpec 字段**: `node_type`、`table`、`id_column`（统一 `"id"`）、`title`、`subtitle`；title/subtitle 取值以 tasks.md 表格为准。
3. **EdgeRule 结构**: `id`、`from_type`、`to_type`、`label`、`match: list[tuple[src_col, dst_col]]`、`direction="out"`、`guard: Optional[str]`、`assumption: Optional[str]`（语义边标注）。
4. **边分类**: 不在 EdgeRule 上单独存 category 枚举；guard 边以 `guard is not None` 区分，语义边以 `assumption is not None` 区分，其余为平凡边。加载时 guard 边 MUST 有 guard 声明。
5. **SQL 生成**: 仅生成单表 SELECT（目标 NodeSpec.table），WHERE 由 match 驱动；guard 边对源列值按逗号 split + strip 后生成 `dst_col IN (?, ?, …)`；所有值走 `%s` 占位符（PyMySQL 风格）。
6. **LIMIT**: 由 `limit` 参数注入 SQL 末尾，不使用字符串拼接节点值；limit 在生成器入口做 int 校验。
7. **SELECT 列**: `id_column`、`title`、`subtitle` 三列，别名保持原列名，供上层统一消费。
8. **校验时机**: 模块 import 时执行注册表自检（14 类型齐全、规则引用合法、id 唯一、guard 完整）；测试覆盖 spec 中全部 Scenario。
9. **Deferred 明确排除**: 反向(in)/双向(both)遍历、interceptor context guard、module_parameter 边、语义假设的数据校验 — 均不在本 change 范围。

## Open Questions

1. **guard 拆分空值**: `before_beans` 为空字符串或仅含逗号时，应返回空结果 SQL（`WHERE 1=0`）还是抛错？→ 建议返回空结果（0 行），与「无邻居」语义一致，测试中覆盖。
2. **未知 nodeType 查找**: 按 spec「未知类型返回空/报错」— 建议查找函数返回 `None`，加载校验与 expand 调用方各自抛 `ValueError`，保持 API 简洁。
3. **assumption 字段形态**: 用语义边专用 `assumption: str` 还是通用 `metadata: dict`？→ 本切片用 `assumption: Optional[str]` 足够，避免过度抽象。
4. **与 ER.md 的差异**: ER 图标注 bridge→java_class，实际规则为 bridge→bean（before_beans→bean_id）；以本 change 的 spec/tasks 为准，ER.md 修正留后续文档 change。
