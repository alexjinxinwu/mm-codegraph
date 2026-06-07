## Design Summary

为 codegraph 提供浏览器端**入口外壳**：持久三栏布局（搜索栏 / 主画布 / 状态区），加上 schema 选择器与 kind+value 搜索控件，调用已有 **GET `/api/v1/resolve`** 把外部标识解析为图根节点。界面 MUST 完整表达 resolve 三态（`found` / `multiple` / `notFound`）及加载/错误态；唯一职责是把**种子节点**交给画布占位接口，图的渲染与 `/expand` 展开留给后续 canvas 变更。

技术选型：**React + Vite + TypeScript** 独立前端包，通过 REST 消费 `codegraph-server`；画布区域仅暴露 `onSeed(node)` 契约与占位展示。

## Alternatives Considered

### Alternative A: React SPA（Vite）+ REST 消费 /resolve

- **Approach**: 在 `codegraph_web/`（或 `frontend/`）搭建 Vite 应用；schema 列表来自 `GET /api/v1/schemas`；搜索提交调用 `/api/v1/resolve`；状态机驱动三态 UI；画布为占位组件接收 `{ type, id, title?, subtitle? }`。
- **Pros**:
  - 与后续 canvas（图渲染、交互展开）天然契合，组件化扩展成本低
  - 与 Python FastAPI 后端解耦，可独立 dev/build/test
  - 三态、候选消歧、加载/错误等交互在客户端状态机中表达清晰
- **Cons**:
  - 需 CORS 或 dev proxy 配置
  - 多一个构建产物与部署步骤
- **Why chosen**: 本切片只做 shell+search，但 roadmap 明确有 canvas；SPA 是长期最省重构的路径

### Alternative B: FastAPI 模板 + HTMX 服务端渲染

- **Approach**: 在 `codegraph_server` 内用 Jinja2 模板 + HTMX 片段实现搜索栏与三态 HTML  partial；几乎无前端构建链。
- **Pros**:
  - 零 Node 工具链，部署单一 Python 进程
  - 首屏简单，适合极薄 UI
- **Cons**:
  - 后续 canvas（力导向图、拖拽、增量 merge）在 HTMX 下成本陡增
  - 三态与候选选择器的交互易变成模板+片段 spaghetti
  - 与已分离的 graph-api 契约测试/front-end 单测生态不匹配
- **Why not chosen**: 与 deferred canvas 能力冲突，短期省构建、长期还债

### Alternative C: 单页内联静态 HTML + 原生 fetch

- **Approach**: `codegraph_server/static/index.html` 单文件，无框架，直接 fetch `/resolve`。
- **Pros**: 最快 PoC，无 npm
- **Cons**:
  - 三态/窄屏/可测试性随功能增长迅速失控
  - 无法复用组件给 canvas、详情面板等后续切片
  - tasks 要求的 8 条 UI 测试难以结构化
- **Why not chosen**: 不符合 spec 对布局、三态、测试的结构化要求

## Agreed Approach

**Alternative A: React SPA + `/api/v1/resolve` 只读消费**

```
┌─────────────────────────────────────────────┐
│  SchemaSelect │ KindSelect │ ValueInput │ Go │
├─────────────────────────────────────────────┤
│                                             │
│           CanvasPlaceholder                 │
│     (接收 seed: GraphNode, 占位展示)         │
│                                             │
├─────────────────────────────────────────────┤
│  Status: idle | loading | empty | error     │
│          | multiple-candidates              │
└─────────────────────────────────────────────┘
```

1. **布局**: 顶栏搜索 + 中部画布占位 + 底/侧状态区（found 时状态区可折叠为 idle）。
2. **Schema**: `GET /api/v1/schemas` 填充下拉；未选 schema 禁用提交。
3. **搜索**: kind ∈ `{ commandId, flowId }`（与 ENTRY_RESOLVERS 对齐，前端常量镜像，后续可改为配置接口）；value 非空校验。
4. **三态**:
   - `found` → `roots[0]` 作为 seed 传给画布
   - `multiple` → 状态区渲染候选列表（title/subtitle），选中后作为 seed
   - `notFound` → 空状态文案，非 error 样式
5. **加载/错误**: 请求中 disable 提交；HTTP/网络失败 → error 区 + 重试（重放最后一次合法参数）。
6. **边界**: 本变更**不**调用 `/expand`；画布只显示 seed 摘要（type/id/title），不画 ER 边。

## Key Decisions

1. **前端栈**: React 18 + Vite + TypeScript；测试用 Vitest + React Testing Library（覆盖 tasks §6 场景）。
2. **目录**: 新增 `codegraph_web/` 包，与 `codegraph_server/` 并列；生产构建产物可由 FastAPI `StaticFiles` 挂载（apply 阶段定具体路径）。
3. **API 契约**: 严格对齐 `ResolveResponse` — `{ status, roots, candidates }` 与 `GraphNodeOut` 字段；seed 类型与 expand 输入 `{ type, id }` 兼容。
4. **Kind 选项**: v1 硬编码 `commandId` / `flowId`；与后端 ENTRY_RESOLVERS 保持同名，不加未注册 kind。
5. **画布接口**: `CanvasPlaceholder` 接收 `seed: GraphNode | null` prop；对外导出类型供后续 canvas 变更替换实现。
6. **响应式**: 窄屏下搜索栏可 stack，画布 min-height 保证可访问，禁止横向 scroll overflow。
7. **Deferred**（不在本 change）: 图渲染、/expand、详情面板、搜索历史、URL 深链、跨 kind 统一搜索。

## Open Questions

1. **Schema 列表**: `GET /api/v1/schemas` 返回格式是否已稳定？→ apply 时读 routes 实装并对齐类型；若缺字段则前端仅展示 name。
2. **生产部署**: dev 用 Vite proxy 指 `localhost:8000`；生产是 FastAPI 同域挂载 static 还是独立 CDN？→ plan 阶段定一种默认（推荐同域挂载）。
3. **候选上限**: resolve 后端 LIMIT=50；multiple UI 是否需虚拟列表？→ v1 全量列表即可，超 50 由 API 截断并在 UI 注明（可选 copy）。
4. **CORS**: 本地 dev 是否已在 FastAPI 启用 CORSMiddleware？→ apply 时若无则加最小 CORS 或仅依赖 Vite proxy。
