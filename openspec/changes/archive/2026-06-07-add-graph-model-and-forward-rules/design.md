## Context

mm-codegraph 将 Java/Spring 代码库索引为 MySQL 14 表 ER 图。上层探索能力（入口解析 `/resolve`、逐层展开 `/expand`、前端渲染）需要一份对「节点长什么样」和「节点之间有哪些边」的统一声明式描述。

当前 `codegraph_core` 已有：
- `models.py` — 14 种实体的 TypedDict 行模型
- `query_engine.py` — `QueryEngine.q(schema, sql, params)` 只读查询原语
- `schema_validator.py` — schema 名校验

尚无图元数据注册表与 expand SQL 生成器；MCP/HTTP 若各自写 SQL 会导致重复与漂移。本 change 在 core 层补齐图模型内核，为后续 resolve/expand 端点提供共享基础。

ER 关系真源：`codegraph_mcp/ER.md`；本 change 的边规则以 `tasks.md` / `specs/graph-core/spec.md` 为准（含 bridge→bean guard 边等 ER 图未完整表达的语义）。

## Goals / Non-Goals

**Goals:**

- 注册 14 种 NodeSpec（table、id_column、title、subtitle）
- 注册 19 条 forward(out) EdgeRule（平凡 16 + 语义 2 + guard 1）
- 实现 `build_expand_query(rule, node, limit) -> tuple[str, tuple]`，参数化、带 LIMIT
- 模块加载时 fail-fast 校验（类型覆盖、规则引用、id 唯一、guard 完整）
- 单元测试覆盖 spec 中全部 Scenario

**Non-Goals:**

- 反向(in)/双向(both)遍历及对应 SQL 生成
- interceptor context 等其余 guard / 带 WHERE 拆分条件的边
- module_parameter 的关系边（孤岛节点）
- HTTP/MCP 端点暴露（本 change 仅内核）
- 语义边假设的实际数据校验
- 修改 MySQL schema 或 ER 文档

## Decisions

### 1. 包结构：`codegraph_core/graph/`

```
codegraph_core/
  graph/
    __init__.py          # 导出公开 API
    node_specs.py        # NODE_SPECS 注册表 + get_node_spec + validate
    edge_rules.py        # EDGE_RULES 注册表 + get_edges_from + validate
    expand_query.py      # build_expand_query
    types.py             # NodeSpec, EdgeRule dataclass（可选，或内联在各自模块）
  models.py              # 不变 — 行级 TypedDict
  query_engine.py        # 不变 — 消费方调用 q() 执行生成 SQL
```

**Rationale**: 图元数据与应用层实体模型职责分离；`graph/` 子包便于后续添加 reverse 规则而不污染 query_engine。

### 2. NodeSpec 用 `@dataclass(frozen=True)`

```python
@dataclass(frozen=True)
class NodeSpec:
    node_type: str
    table: str
    id_column: str
    title: str
    subtitle: str
```

静态 dict `NODE_SPECS: dict[str, NodeSpec]` 在模块末尾注册 14 项；`get_node_spec(node_type) -> NodeSpec | None`。

**Rationale**: frozen dataclass 不可变、可哈希，便于测试断言；比 TypedDict 更适合元数据（非 DB 行）。

### 3. EdgeRule match 为显式 `(src_col, dst_col)` 元组列表

```python
@dataclass(frozen=True)
class EdgeRule:
    id: str
    from_type: str
    to_type: str
    label: str
    match: tuple[tuple[str, str], ...]
    direction: str = "out"
    guard: str | None = None
    assumption: str | None = None
```

- 单列边：`match=(("chain_id", "chain_id"),)`
- 复合键：`match=(("flow_id", "flow_id"), ("state_name", "state_name"))`
- 语义边：额外设 `assumption="假设 activities.logic 存 chain_id,待校验"`
- guard 边：设 `guard="split_comma"`（或描述性字符串），加载时 `guard is not None` 即视为 guard 边

**Rationale**: 显式映射支持列异名与多列 AND；assumption 与 guard 分字段，避免过度通用的 metadata dict。

### 4. SQL 生成策略

**平凡边 / 语义边** — 对每个 `(src, dst)` in match：

```sql
SELECT `{id}`, `{title}`, `{subtitle}`
FROM `{target_table}`
WHERE `{dst}` = %s [AND `{dst2}` = %s ...]
LIMIT %s
```

参数顺序：按 match 顺序取 `node[src]` 值，最后 append limit。

**guard 边** — 对 `before_beans` 等源列：

1. `values = [v.strip() for v in node[src_col].split(",") if v.strip()]`
2. 若 `values` 为空 → `WHERE 1=0`（返回空集，不抛错）
3. 否则 → `WHERE `{dst}` IN (%s, %s, ...)` + LIMIT

**安全**: 节点字段值与 limit 均通过 `%s` 绑定；表名/列名来自静态注册表（非用户输入），可用反引号包裹。

### 5. 校验在模块 import 时执行

`graph/__init__.py` import 链末尾调用 `_validate_registries()`：

| 检查项 | 行为 |
|--------|------|
| NodeSpec 恰好 14 种 | 缺/多 → `RegistryError` |
| 每种 id_column、table 非空 | → `RegistryError` |
| EdgeRule from/to 存在于 NODE_SPECS | → `RegistryError` |
| EdgeRule id 全局唯一 | → `RegistryError` |
| guard 边 guard 非空 | → `RegistryError` |

**Rationale**: fail-fast 保证不完整规则不会静默进入生产；测试可通过 import 触发。

### 6. 测试布局

```
codegraph_core/graph/test_node_specs.py
codegraph_core/graph/test_edge_rules.py
codegraph_core/graph/test_expand_query.py
```

使用 pytest；expand 测试断言 SQL 字符串与 params 元组（快照或结构化断言），不依赖真实 MySQL（除非项目已有 DB fixture 惯例）。

### 7. 与 QueryEngine 集成方式（本 change 不实现调用方）

```python
sql, params = build_expand_query(rule, node, limit=200)
rows = engine.q(schema, sql, params)
```

上层 resolve/expand change 负责：选 rule → 取 node 行 → 调用生成器 → 执行。

## Risks / Trade-offs

[Risk] 语义边假设（logic 列存 chain_id）与真实数据不符 → Mitigation: assumption 字段显式标注；后续独立 change 做数据校验；expand 结果可能为空但不 crash。

[Risk] guard 边 comma-split 对异常格式（空格、重复 id）行为不一致 → Mitigation: strip 空白、去空串；重复 id 不影响 IN 语义；测试覆盖单值/多值/空值。

[Risk] 静态注册表与 DB schema 漂移 → Mitigation: 14 表名与 tasks.md 表格对齐 ER.md；schema 变更时同步更新注册表并跑全量测试。

[Risk] SQL 注入 via 列名 → Mitigation: 列名/表名仅来自静态注册表，不接收用户输入；值一律参数绑定。

## Migration Plan

1. 新增 `codegraph_core/graph/` 模块与类型定义
2. 实现 NODE_SPECS（tasks §1.2 表格）+ 校验
3. 实现 EDGE_RULES（tasks §2.2–2.5 表格）+ 校验
4. 实现 `build_expand_query` + 单元测试（tasks §4）
5. 在 `codegraph_core/__init__.py` 可选导出 `build_expand_query`、`get_node_spec`、`get_edges_from`
6. 无 DB migration；无 MCP/HTTP 变更；现有功能不受影响

**Rollback**: 删除 `graph/` 子包即可，无持久化状态。

## Open Questions

1. guard 拆分策略是否需支持除逗号外的分隔符？→ 本切片仅逗号；bridge.before_beans 数据格式已确认。
2. expand 是否需返回 rule.label 供前端展示？→ 本 change 生成器只返回 SQL；label 由调用方从 rule 对象读取。
3. LIMIT 默认值是否与 QueryEngine.DEFAULT_LIMIT(200) 统一？→ 调用方传入；生成器不设默认，避免隐式行为。
