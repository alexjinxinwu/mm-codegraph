## Why

入口解析(/resolve)只能给出一个根节点,真正的「探索」靠的是从任意已知节点沿 ER
边逐层点开邻居。本能力提供 POST /expand:输入一个起点节点,按 graph-core 的
forward 边规则,返回它在图上的直接邻居,作为可增量合并进前端画布的
{ nodes, edges }。

graph-core 已经把「节点长什么样」(NodeSpec)与「节点之间有哪些 forward 边」
(EDGE_RULES)以及「一条边 + 一个起点 → 参数化 SQL」(build_expand_query)都备好了。
本能力是把这三者接到 HTTP 上的最薄一层:选边、水合起点、执行、整形、去重、封顶。

一个由 graph-core 数据模型决定的事实直接影响本端点的形状:NodeSpec 的 id 列仅作
行身份(前端去重与点选),不参与任何关联;边的关联建立在业务列上(flow_id、
chain_id、bean_class……),且 build_expand_query 需要起点节点的业务列取值。因此
/expand 在拿到 { type, id } 后,MUST 先按 id 从该节点对应表水合出源列值,再交给
生成器——客户端无需知道哪些列是 join 键。

本能力依赖 graph-core(NodeSpec / EDGE_RULES / build_expand_query)与共享查询内核
(extract-query-core)。它只读,不修改数据库。

## What Changes

- 新增 POST /expand,输入 { schema, node: { type, id }, edgeIds? },返回沿 forward
  ER 边得到的邻居增量 { nodes, edges }。
- 展开由 graph-core 的 EDGE_RULES 驱动:选出所有以 node.type 为 from 的 forward 边
  (平凡单列、复合键、语义、guard 四类皆含);提供 edgeIds 时仅展开指定边。
- 水合(hydrate):按 NodeSpec.id_column(id)从起点节点对应表取出该行,得到边规则
  所需的全部源列业务值,再调用 build_expand_query。
- 每条边经 build_expand_query + 共享查询内核执行;结果整形为 nodes
  (type / id / title / subtitle)与 edges(ruleId / from / to / label)。
- 节点按 (type, id) 去重;每条边带硬编码安全上限,避免单点邻居过多撑爆响应。
- 全部取值(起点 id、水合得到的源列值、guard 拆分元素)以绑定参数传入。

## Deferred(后续 change)

- direction=in / both 的反向、双向展开(随 graph-core 反向规则一并落地)。
- 客户端分页:offset / hasMore 续拉超上限的邻居。
- 展开结果的服务端缓存与批量多起点展开。
- 节点详情增强(副标题之外的更多元数据)。

## Impact

- Affected specs: 在 `graph-api` capability 下新增 /expand 相关需求。
- Affected code: HTTP 路由层 /expand handler、起点水合逻辑、结果整形与去重。
- 依赖 graph-core 与 extract-query-core,均为只读,无数据库结构变更。