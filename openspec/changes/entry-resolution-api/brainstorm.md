## Design Summary

在 graph-core 之上新增 **ENTRY_RESOLVERS** 注册表与 **GET `/api/v1/resolve`**，把外部业务标识（commandId、flowId）解析为图根节点 `{ type, id, title, subtitle }`，供 `/expand` 直接消费。解析结果统一三态：`notFound` / `found` / `multiple`（多命中列 candidates 供前端消歧）。业务逻辑放 `codegraph_core/graph/resolve_service.py`，HTTP 层薄适配；与 expand 变更对称，不修改 graph-core 注册表。

## Alternatives Considered

### Alternative A: ENTRY_RESOLVERS 注册表 + GET /resolve（与 EDGE_RULES 同构）

- **Approach**: 声明式 `EntryResolver(kind, node_type, match_column)`；`resolve_entry(schema, kind, value)` 生成参数化 SELECT，按行数判定三态，用 NodeSpec 整形。
- **Pros**:
  - 新增入口种类只加注册表项，不改端点
  - 与 graph-core / expand 分层一致，MCP 可复用
  - 三态语义显式，覆盖 flowId 多命中等真实场景
- **Cons**:
  - 需维护第二张注册表及加载校验
  - GET 查询参数对极长 value 略 awkward（本切片可接受）
- **Why chosen**: proposal/spec 已定；与 EDGE_RULES 设计哲学一致

### Alternative B: 复用现有 GET 端点（find_service_entry / get_flow）

- **Approach**: 不新增 /resolve；前端按 kind 调用不同 REST 路径，各自解析。
- **Pros**: 零新端点，现有 routes 已有部分逻辑
- **Cons**:
  - 无统一三态（found/multiple/notFound）
  - 节点形态与 /expand 不一致，需前端适配
  - 每加一种入口加一条 route，与 ENTRY_RESOLVERS 目标相反
- **Why not chosen**: 无法保证「解析 → 展开」契约闭环

### Alternative C: POST /resolve + JSON body（与 /expand 对称）

- **Approach**: `POST /api/v1/resolve` body `{ schema, kind, value }`，其余同 A。
- **Pros**: 与 expand 请求风格统一；value 长度无 URL 限制
- **Cons**:
  - spec/proposal 已定为 GET query；语义上 resolve 幂等读操作 GET 也合理
  - 改动 spec 成本
- **Why not chosen**: 遵循已有 proposal；GET 对本切片足够

## Agreed Approach

**Alternative A: ENTRY_RESOLVERS + GET /api/v1/resolve**

1. **`codegraph_core/graph/entry_resolvers.py`** — 注册 commandId、flowId 两条 resolver + 加载校验
2. **`codegraph_core/graph/resolve_service.py`** — `resolve_entry()` → `{ status, roots, candidates }`
3. **`GET /api/v1/resolve`** — query: `schema`, `kind`, `value`；校验后委托 service
4. **节点 type** 使用 graph-core NodeSpec 名：`service_entry`（非 `service_entries`）、`flow`（非 `flows`）— delta spec 中 table 名误作 nodeType 处实现时修正

## Key Decisions

1. **端点**: `GET /api/v1/resolve?schema=&kind=&value=`（router prefix 与 expand 一致）。
2. **EntryResolver 结构**: `kind`, `node_type`, `match_column`；表/title/subtitle 从 NodeSpec 读取，不重复声明。
3. **commandId resolver**: `node_type=service_entry`，`WHERE command_id = %s`（精确匹配）。
4. **flowId resolver**: `node_type=flow`，`WHERE flow_id = %s`；多行 → `multiple`。
5. **三态**:
   - 0 行 → `notFound`, `roots=[]`, `candidates=[]`, HTTP 200
   - 1 行 → `found`, `roots=[node]`, `candidates=[]`
   - 2+ 行 → `multiple`, `roots=[]`, `candidates=[...]`
6. **整形**: 与 expand 邻居节点相同 — `{ type, id, title, subtitle }`，复用共享 helper（可抽 `shape_node_row(node_type, row)`）。
7. **校验**: schema 格式（SchemaValidator）、kind 已注册、value 非空；失败 422，不查库。
8. **LIMIT**: resolver 查询加安全上限（如 50）以防 multiple 爆炸；超上限仍返回 multiple，candidates 截断（或全量若 ≤ limit）。
9. **Deferred**: bean/java_class 等 resolver、跨 kind 搜索、模糊匹配、候选分页。

## Open Questions

1. **flowId 多命中语义**: 同一 `flow_id` 在 `flows` 表多行是否常见？→ v1 按行数三态；若业务上 flowId 应查 service_entries，后续加 `flowId→service_entry` resolver 或新 kind。
2. **spec nodeType 笔误**: delta spec 写 `service_entries`/`flows` → 实现与 graph-core 对齐为 `service_entry`/`flow`，sync 主 spec 时修正。
3. **共享 shape helper**: 从 expand_service 抽 `shape_node(node_type, row)` 到 `graph/shape.py`？→ apply 时若重复则抽取，避免双份整形逻辑。
