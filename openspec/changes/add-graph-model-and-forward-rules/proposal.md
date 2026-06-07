## Why

整个探索系统建立在一张 ER 图之上:节点是数据库里的实体(service_entry、flow、
state、logic……),边是实体之间的引用关系。所有上层能力——入口解析(/resolve)、
逐层展开(/expand)、前端渲染——都依赖一份对「节点长什么样」和「节点之间有哪些
边」的统一、声明式描述。

若没有这层描述,SQL 会散落各处、每加一种关系都要改多处,且无法保证入口解析返回
的根节点能被展开端点正确消费。本能力把图模型集中成两张注册表(NodeSpec 与
EDGE_RULES),并提供一个把「一条边 + 一个起点节点」翻译成参数化 SQL 的生成器。

真实 schema 的几个事实决定了数据结构:

1. 每张表都有自增主键 id,但 id 仅用于行的唯一标识(前端去重、点选),不参与任何
   表间关联。表间关系一律建立在业务列上(flow_id、chain_id、bean_id……),且两端
   列名常不一致(bean_class→full_qualified_name、bean_ref→bean_id)。因此「节点
   身份」与「边的关联列」必须分离:NodeSpec 用 id 表达身份,EdgeRule 用显式
   「源列→目标列」映射表达关联。
2. 部分关系是单列等值,部分是多列复合(state 需 flow_id + state_name)。
3. 部分关系列语义依赖外部约定(activities.logic / flow_tasks.logic 假设存放
   chain_id),需在规则上显式标注假设,以便后续以数据校验。
4. 个别关系的源值并非单一值,而是逗号分隔的列表(bridges.before_beans 假设为
   bean_id 列表),匹配前需先拆分。

本能力为纯内核逻辑,不涉及 HTTP,也不修改数据库,可与共享查询内核
(extract-query-core)并行开发。

## What Changes

- 新增 14 种节点类型的 NodeSpec,声明每种节点的自增主键列(id,仅作行身份)、
  图上显示用的标题字段与副标题字段。
- 新增 EDGE_RULES 注册表,编码 forward(out)三类边:
    - 平凡边:14 条单列等值边 + 2 条复合键边,覆盖 service_entry 经 bean 到
      java_class/java_method 的主路线,以及 flow 子树。
    - 语义边:logic→activity、logic→flow_task,以列异名 match(chain_id→logic)
      表达,并在规则上显式标注「假设 logic 列存 chain_id,待数据校验」。
    - guard 边:bridge→bean,源列 before_beans 假设为逗号分隔 bean_id 列表,
      guard 声明拆分 + 逐项匹配。
- EdgeRule 的 match 以显式「源列→目标列」列表表达关联,支持列异名与多列复合。
- EdgeRule 包含 direction 与 guard 字段;本能力中 direction 固定为 out,guard
  仅在 guard 边上启用。
- 新增 build_expand_query(rule, node, limit),根据一条 forward 边规则与一个起点
  节点生成参数化 join 查询:平凡边/语义边生成等值条件,guard 边生成 IN 条件;
  所有取值以绑定参数传入,并带安全上限 LIMIT。

## Deferred(后续 change)

- 反向(in)与双向(both)遍历的规则方向与 SQL 生成。
- interceptor context 等其余 guard / 带 WHERE 拆分条件的边。
- module_parameter 的关系边(module_id 当前未连接任何表,暂为孤岛节点)。
- 节点详情字段增强(展示用副标题之外的更多元数据)。
- 对语义边假设(activities.logic / flow_tasks.logic 存 chain_id)的实际数据校验。

## Impact

- Affected specs: 新增 `graph-core` capability。
- Affected code: 图模型模块(NodeSpec 注册表、EDGE_RULES 注册表、
  build_expand_query 生成器)。
- 只读,无数据库结构变更,无对外 HTTP 接口。