## Design Summary

在 `codegraph-server` 新增 **POST `/api/v1/expand`**，作为图探索的统一 forward 展开入口。客户端提交 `{ schema, node: { type, id }, edgeIds? }`；服务端先按 NodeSpec 水合起点行（取得边规则所需的业务源列），再对每条适用的 forward 边调用 graph-core 的 `build_expand_query` + `QueryEngine.q()`，将邻居整形为 `{ nodes, edges }` 返回。本 change **仅 HTTP 端点 + 编排层**，不修改 graph-core 注册表或 SQL 生成逻辑；MCP 对等工具留后续 change。

## Alternatives Considered

### Alternative A: 薄编排层 + graph-core 内核（POST /expand）

- **Approach**: 在 `codegraph_core/graph/` 新增 `expand_service.py`（水合、选边、执行、整形、去重）；`codegraph_server/routes.py` 仅做 HTTP 绑定与校验。
- **Pros**:
  - 与 graph-core spec 设计一致，MCP 后续可复用同一 service
  - 现有 per-entity 路由（`get_flow`、`resolve_chain`）保留，逐步迁移前端
  - 测试可分层：service 单测 + HTTP 集成测
- **Cons**:
  - 需定义统一的 node/edge JSON 形态
  - 水合 SQL 需从 EDGE_RULES 推导所需源列并集
- **Why chosen**: 上一 change 已明确「上层 resolve/expand 共用内核」；本方案最直接落地 tasks/spec

### Alternative B: 在 routes 内联展开逻辑（无 service 层）

- **Approach**: 全部逻辑写在 `routes.py` 的 `/expand` handler 内，直接 import graph-core。
- **Pros**: 文件少、上线快
- **Cons**:
  - MCP 无法复用；与现有 `routes.py` 已偏 fat 的问题叠加
  - 难以对水合/去重写不依赖 HTTP 的单元测试
- **Why not chosen**: 与 refactor 后「core 承载业务、server 薄适配」方向冲突

### Alternative C: 继续扩展资源型 GET 端点（不引入 /expand）

- **Approach**: 为每种 nodeType 增加 `GET .../flows/{id}/states` 等专用端点，手写 SQL（类似现有 `get_state`）。
- **Pros**: 与现有 API 风格一致，单条路径直观
- **Cons**:
  - 19 条边 × 多种 type ≈ 重复爆炸；guard/语义边难以统一
  - 前端无法「传 node + 可选 edgeIds」通用展开，与 ER 图交互模型不符
- **Why not chosen**: graph-core 的存在就是为了消除这类散落 SQL；本 change 目标正是统一 expand

## Agreed Approach

**Alternative A: 薄编排层 + graph-core 内核**

1. **`codegraph_core/graph/expand_service.py`**（或 `graph/expand.py`）— `expand_neighbors(schema, node, edge_ids?, limit?) -> ExpandResult`
2. **`POST /api/v1/expand`** — 请求/响应 Pydantic 模型，校验后委托 service
3. **水合**：`SELECT` 起点表行，列 = 该 type 所有 forward 边的 match 源列并集 + title/subtitle
4. **展开**：`get_edges_from(type)` ∩ `edgeIds`（若提供）→ 每条 `build_expand_query` → `q()`
5. **整形**：邻居 → `{ type, id, title, subtitle }`；边 → `{ ruleId, from, to, label }`；去重与 LIMIT 按 spec

## Key Decisions

1. **端点路径**: `POST /api/v1/expand`（与现有 router prefix 一致，非根路径 `/expand`）。
2. **nodeType 命名**: 使用 graph-core 注册的 14 种 kebab/snake 名（`flow` 非 `flows`，`service_entry` 等）；spec 中 `flows` 为笔误，实现与 graph-core 对齐。
3. **起点标识**: 客户端只传 `{ type, id }`，id 为表自增主键；关联列由服务端水合，客户端不传 business keys。
4. **edgeIds 可选**: 缺省展开该 type 全部 forward 边；传入则 filter 交集，且每条 MUST 满足 `rule.from_type == node.type`。
5. **notFound 语义**: 起点 id 不存在 → `{ nodes: [], edges: [] }`，HTTP 200（非 404），与 spec 一致。
6. **校验错误**: 未知 schema / nodeType / edgeId → 4xx + 明确 message，**不查库**。
7. **LIMIT**: 硬编码常量（如 200，与 `QueryEngine.DEFAULT_LIMIT` 对齐），经 `build_expand_query` 注入；超限静默截断。
8. **本 change 范围外**: MCP `expand` tool、`/resolve` 入口解析、反向(in)边、module_parameter 边。

## Open Questions

1. **schema 允许列表**: 沿用 `SchemaValidator` / 动态 `list_schemas`，还是 env 白名单？→ 建议与现有 `/schemas` 一致：校验格式 + DB 存在性（或 `SHOW DATABASES` 命中）。
2. **edge.from / edge.to 形态**: `{ type, id }` 对象还是扁平字段？→ 建议 `{ type, id }` 对象，与 node 输入对称，便于前端图库。
3. **水合列缺失**: 行存在但某源列为 NULL → 该边 expand 返回空邻居，不 fail 整条请求。
4. **是否同步改 proposal.md**: 当前 `proposal.md` 为空文件但 status 为 done — continue 后应补写 proposal 或 ff 修复 artifact 链。
