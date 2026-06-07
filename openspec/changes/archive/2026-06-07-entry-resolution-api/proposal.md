## Why

探索从一个根节点开始。用户手里通常只有一个业务标识——一个 commandId,或一个
flowId——而不是图节点本身。本能力把这类外部标识解析成 graph-core 的根节点,作为
/expand 的起点。没有它,前端无从落第一个节点。

入口标识不止一种,而且不一定唯一:同一个 flowId 可能被多个 service_entry 引用,
按人类可读标识查询也可能命中多行。因此解析必须能表达「无命中 / 唯一命中 /
多命中待消歧」三态,而不是假定一对一。

为避免每加一种入口就改一次端点,本能力引入 ENTRY_RESOLVERS 注册表(与 graph-core
的 EDGE_RULES 同构):每种入口声明 kind、目标 nodeType、以及「外部值 → 查询」的
映射。端点本身只做:选 resolver → 执行 → 整形 → 判定三态。新增入口种类是往注册表
加一条,不动端点。

本能力依赖 graph-core(NodeSpec,用于把命中行整形成节点)与共享查询内核
(extract-query-core)。它只读,不修改数据库。

## What Changes

- 新增 GET /resolve?schema=&kind=&value=,把一个外部标识解析为根节点。
- 新增 ENTRY_RESOLVERS 注册表;本切片注册两种入口:
  - kind=commandId → 解析到 service_entries 节点
  - kind=flowId → 解析到 flows 节点
- 统一三态返回:notFound(0 命中)、found(1 命中,roots 含该节点)、
  multiple(多命中,candidates 列出候选供前端消歧)。
- 命中行用目标 NodeSpec 整形为 { type, id, title, subtitle },与 /expand 的节点
  形态一致,可不加转换直接作为 /expand 的输入。
- 外部 value 以绑定参数传入。

## Deferred(后续 change)

- 更多入口种类(如按 bean、按 java_class 解析),届时只往 ENTRY_RESOLVERS 加规则。
- 跨 kind 的统一搜索(不指定 kind、模糊匹配多种入口)。
- 候选分页(当 multiple 命中数极多时)。
- 模糊 / 前缀匹配(本切片为精确匹配)。

## Impact

- Affected specs: 在 `graph-api` capability 下新增 /resolve 相关需求。
- Affected code: HTTP 路由层 /resolve handler、ENTRY_RESOLVERS 注册表、结果整形。
- 依赖 graph-core 与 extract-query-core,均为只读,无数据库结构变更。