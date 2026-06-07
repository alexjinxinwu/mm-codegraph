## Design Summary

在 `codegraph_web/` 用 **React Flow** 替换 `CanvasPlaceholder`，实现增量 ER 图画布：接收 browser-shell 的 **seed** 作为初始单节点，点击节点调用 **POST `/api/v1/expand`**，将 `{ nodes, edges }` 去重并入图状态，并对被点击节点展示独立的加载/错误/已展开态。布局采用 **dagre** 做增量分层布局，新邻居落在展开节点附近，已有节点坐标尽量保留以减少跳动。

图状态与展开交互分离：`useGraphStore` 管节点/边集合与去重 merge；`useNodeExpand` 管 per-node 异步展开与重试。本 change 不实现详情面板、折叠子树、URL 深链。

## Alternatives Considered

### Alternative A: React Flow + dagre 增量布局

- **Approach**: `@xyflow/react` 渲染节点/边；自定义 node 类型展示 title/subtitle；点击 → `expandEntry(schema, node)` → merge 去重 → `dagre` 仅对新子树或局部重算位置，保留已有 `position`。
- **Pros**:
  - 与现有 React/Vite 栈一致；点击、选中、per-node UI 成熟
  - 增量图探索是 React Flow 常见模式
  - 社区示例多（expand-on-click、dedupe by id）
- **Cons**:
  - 依赖体积较纯 SVG 大
  - dagre 全量重排时需额外逻辑保稳定
- **Why chosen**: 最匹配 spec 的「点击展开 + 每节点态 + 增量 merge」

### Alternative B: Cytoscape.js + fcose/cose-bilkent 布局

- **Approach**: `react-cytoscapejs` 渲染；布局引擎自动排布；tap 触发展开。
- **Pros**: 布局算法强，大图表现好
- **Cons**:
  - React 集成与受控状态较 awkward
  - 「已有节点位置稳定」需手动 `preset` 坐标，复杂度高
  - 包体积与 learning curve
- **Why not chosen**: 增量稳定布局成本高于 A，对 v1 过度

### Alternative C: 自绘 SVG + 手动坐标

- **Approach**: 纯 SVG/canvas；边用直线；新节点 polar 排列在父节点周围。
- **Pros**: 零图库依赖，增量坐标完全可控
- **Cons**:
  - 边路由、缩放平移、命中测试需自研
  - 14 种 node type 样式与交互测试成本高
  - 与 tasks §6 九条 UI 测试难维护
- **Why not chosen**: 重复造轮子，延误 canvas 交付

## Agreed Approach

**Alternative A: React Flow + dagre**

```
App
 ├── schema (lifted from SearchBar)
 ├── seed from useResolveSearch
 └── GraphCanvas
       ├── useGraphStore(nodes, edges, merge, dedupe)
       ├── useNodeExpand(schema, expandNode)
       └── ReactFlow
             ├── CodegraphNode (title/subtitle, type badge, expand spinner/error)
             └── CodegraphEdge (label from expand response)
```

**数据流**:

1. **Seed 变更** → 重置图 store，单节点 `(type,id)` 居中，无边，`expanded=false`
2. **点击未展开/可重试节点** → 该 nodeId 进入 `loading` → POST `/api/v1/expand` `{ schema, node: { type, id } }`
3. **成功** → merge nodes/edges（键：`${type}:${id}` / `${ruleId}:${from}:${to}`）→ 标记 `expanded=true` → 局部 dagre → 更新 positions
4. **失败** → 该节点 `error` + retry；其它节点可继续点击
5. **重复点击 loading 中节点** → no-op

**与 browser-ui 集成**: `App.tsx` 将 `CanvasPlaceholder` 换为 `GraphCanvas`，传入 `schema`、`seed`；SearchBar 的 schema 选择 **提升到 App**（expand 需要同一 schema）。

## Key Decisions

1. **图库**: `@xyflow/react`（React Flow v12+）
2. **布局**: `@dagrejs/dagre`（LR 或 TB），merge 后仅对新节点赋位，已有节点保留 `position` 除非重叠
3. **去重键**: 节点 `(type, id)`；边 `(ruleId, fromType, fromId, toType, toId)` — 对齐 graph-api spec
4. **Expand API 客户端**: `codegraph_web/src/api/expand.ts` 镜像 `ExpandResponse`
5. **Per-node 状态**: `Record<nodeKey, 'idle'|'loading'|'error'>` 挂在 store 或 expand hook
6. **已展开标记**: 成功后置 `expanded=true`；再次点击已展开节点 v1 **不重复请求**（spec 可选 re-expand → v1 跳过）
7. **Type 视觉区分**: CSS class `node-type--${type}` + 14 色板常量（不必 14 图标）
8. **Capability 名**: delta spec 使用 `graph-browser`（画布需求），实现仍在 `codegraph_web/`
9. **Deferred**: 详情面板、折叠、过滤、力导向升级、撤销、URL 深链

## Open Questions

1. **Schema 提升** — 当前 `SearchBar` 内局部 state；apply 时须把 `schema` 升到 `App` 并传给 `GraphCanvas` 与 expand。→ design/plan 明确为前置 refactor。
2. **Seed 切换行为** — 新搜索命中是否清空旧图？→ v1 **是**，seed 变化 reset store。
3. **edgeIds 过滤** — v1 默认展开全部 forward 边（不传 edgeIds）；后续 UI 加边类型筛选。
4. **dagre 稳定性阈值** — 「基本稳定」如何测？→ 测试断言已有节点坐标变化 ≤ ε 或 mock layout 只动新节点。
5. **React Flow 包名** — 使用 `@xyflow/react`（npm 现行包名），非旧 `reactflow`。
