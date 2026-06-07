# Graph Core

## Purpose

在 `codegraph_core/graph/` 提供 ER 图模型的声明式内核：14 种 NodeSpec、19 条 forward(out) EDGE_RULES，以及 `build_expand_query()` SQL 生成器。节点身份（自增 id）与表间关联（业务列 match）分离；上层 `/resolve`、`/expand` 与 MCP/HTTP 共用此内核，避免 SQL 散落与行为漂移。

实现位置：`codegraph_core/graph/`（`node_specs.py`、`edge_rules.py`、`expand_query.py`）。

## Requirements

### Requirement: 节点类型模型

系统 SHALL 为每种 ER 节点类型提供 NodeSpec,声明该类型对应的数据库表、行身份列
(id_column)、图上显示的标题字段(title)与副标题字段(subtitle)。NodeSpec
MUST 覆盖系统支持的全部 14 种节点类型,且每种类型的 id_column 与 table MUST 非空。

每张表均以自增主键 id 作为行身份,该 id 仅用于行的唯一标识(前端去重、点选),
不参与任何表间关联;因此 id_column 统一为 "id"。表间关联一律建立在业务列上,由
边规则(EDGE_RULES)的 match 单独声明,与 id 无关。

#### Scenario: 行身份列统一为自增主键

- **WHEN** 查询 flow 的 NodeSpec
- **THEN** id_column 为 "id"
- **AND** title 为 "flow_id",subtitle 为 "flow_type"

#### Scenario: 行身份与关联分离

- **WHEN** 查询 state 的 NodeSpec
- **THEN** id_column 为 "id"
- **AND** 该节点参与的关联(flow_id + state_name)由边规则的业务列 match 表达,
  不使用 id

#### Scenario: 节点类型覆盖完整

- **WHEN** 枚举所有已注册的 NodeSpec
- **THEN** 恰好包含以下 14 种节点类型:service_entry、flow、logic、bean、
  state、flow_task、activity、transition、logic_step、bridge、java_class、
  interceptor、java_method、module_parameter

#### Scenario: 按类型查找

- **WHEN** 以一个已知 nodeType 查找其 NodeSpec
- **THEN** 返回对应的 table、id_column、title、subtitle 定义

#### Scenario: 身份列不可为空

- **WHEN** 加载 NodeSpec 注册表
- **THEN** 任一节点类型若缺失 id_column 或 table,则加载失败并报错

---

### Requirement: forward 边规则注册表

系统 SHALL 以声明式 EDGE_RULES 注册表表达 ER 图中的 forward(out)边。每条
EdgeRule MUST 包含 id、from、to、label、match,以及 direction 与 guard 字段。
match 是一个「源列→目标列」映射列表,描述如何用起点节点(from)的业务列值约束
目标节点(to)的业务列。match MUST 支持源列与目标列异名,并支持多列复合连接。
本能力中所有规则 direction 固定为 out;反向(in)与双向(both)遍历不在本能力
范围内。

EDGE_RULES 包含三类 forward 边:

1. 平凡边——单列等值直连或复合键直连,源列值与目标列直接等值匹配。
2. 语义边——结构上等同列异名平凡边,但其源列的业务含义依赖外部约定。本能力下
   语义边包括 logic→activity 与 logic→flow_task,二者均假设 activities.logic /
   flow_tasks.logic 列存放 chain_id 值;该假设 MUST 在规则上以注释或元数据显式
   标注,以便后续校验数据。
3. guard 边——源列不是单一值而需先经 guard 声明的变换才能用于匹配。本能力下
   guard 边为 bridge→bean,其源列 before_beans 假设为逗号分隔的 bean_id 列表,
   guard MUST 声明该值需按逗号拆分后逐项匹配目标列。

#### Scenario: 单列等值边

- **WHEN** 查询 logic → bridge 的边规则
- **THEN** 返回一条平凡边,其 match 为 chain_id → chain_id

#### Scenario: 列异名边

- **WHEN** 查询 bean → java_class 的边规则
- **THEN** 返回一条平凡边,其 match 为 bean_class → full_qualified_name

#### Scenario: 复合键边

- **WHEN** 查询 state → activity 的边规则
- **THEN** 返回一条平凡边,其 match 同时包含 flow_id → flow_id 与
  state_name → state_name

#### Scenario: 语义边携带显式假设标注

- **WHEN** 查询 logic → activity 的边规则
- **THEN** 返回一条语义边,其 match 为 chain_id → logic
- **AND** 规则显式标注「假设 activities.logic 列存放 chain_id 值,待数据校验」

#### Scenario: 语义边覆盖 flow_task

- **WHEN** 查询 logic → flow_task 的边规则
- **THEN** 返回一条语义边,其 match 为 chain_id → logic
- **AND** 规则显式标注「假设 flow_tasks.logic 列存放 chain_id 值,待数据校验」

#### Scenario: guard 边声明拆分变换

- **WHEN** 查询 bridge → bean 的边规则
- **THEN** 返回一条 guard 边,其 match 源列为 before_beans、目标列为 bean_id
- **AND** 其 guard 声明 before_beans 需按逗号拆分为多个 bean_id 后逐项匹配

#### Scenario: 主路线连通至 java

- **WHEN** 从 service_entry 出发,沿 forward 边遍历 EDGE_RULES
- **THEN** 存在规则链 service_entry → bean → java_class → java_method

#### Scenario: flow 子树连通

- **WHEN** 从 flow 出发沿 forward 边遍历
- **THEN** 存在规则链 flow → state → activity → transition

#### Scenario: logic 子树连通

- **WHEN** 从 logic 出发沿 forward 边遍历
- **THEN** 存在规则 logic → logic_step、logic → bridge,
  且经 guard 边 bridge → bean 可继续接入 bean 子树

#### Scenario: 规则引用的节点类型必须存在

- **WHEN** 加载 EDGE_RULES
- **THEN** 每条规则的 from 与 to 都能在 NodeSpec 中找到对应定义
- **AND** 若任一规则引用了未定义的节点类型,则加载失败并报错

#### Scenario: 规则 id 唯一

- **WHEN** 加载 EDGE_RULES
- **THEN** 若存在重复的规则 id,则加载失败并报错

#### Scenario: guard 边必须声明 guard

- **WHEN** 加载 EDGE_RULES
- **THEN** 任一被标记为 guard 类别的边若缺少 guard 声明,则加载失败并报错

#### Scenario: 按起点类型筛选边

- **WHEN** 以某个 nodeType 作为 from 查询适用的 forward 边
- **THEN** 返回所有 from 等于该类型的 forward 边规则(含平凡边、语义边、guard 边)

---

### Requirement: forward 展开 SQL 生成器

系统 SHALL 提供 build_expand_query(rule, node, limit),根据一条 forward 边规则
与一个起点节点,生成用于获取其正向邻居的参数化 SQL 查询。起点节点的所有取值
MUST 以绑定参数方式传入,不得通过字符串拼接进入 SQL。生成的查询 MUST 包含由
limit 控制的安全上限,且 SELECT 列表 MUST 覆盖目标节点 NodeSpec 的 id_column、
title 与 subtitle 字段。

对不同类别的边,where 条件的生成规则如下:

- 平凡边与语义边:对 match 中的每一项,生成一个「目标列 = 起点对应源列值」的
  等值条件,多项以 AND 连接。
- guard 边:按 guard 声明先将起点源列值拆分为值列表,再生成「目标列 IN (绑定
  参数列表)」条件;列表中每个元素 MUST 各占一个绑定参数。

#### Scenario: 列异名正向展开

- **WHEN** 对一个 bean 节点按 bean → java_class 边规则生成查询
- **THEN** SQL 查询 java_classes 表中 full_qualified_name 等于该 bean 的
  bean_class 值的行
- **AND** SELECT 列表包含 java_classes 的 id、class_name、package_name

#### Scenario: 复合键展开

- **WHEN** 对一个 state 节点按 state → activity 边规则生成查询
- **THEN** SQL 的 where 同时约束 flow_id 与 state_name 两列,以 AND 连接

#### Scenario: 语义边展开

- **WHEN** 对一个 logic 节点按 logic → activity 边规则生成查询
- **THEN** SQL 查询 activities 表中 logic 等于该 logic 的 chain_id 值的行
- **AND** chain_id 值以绑定参数传入

#### Scenario: guard 边拆分展开

- **WHEN** 对一个 bridge 节点按 bridge → bean 边规则生成查询,
  且其 before_beans 值为多个以逗号分隔的 bean_id
- **THEN** SQL 的 where 为 bean_id IN (...),其中每个拆分出的 bean_id 各占一个
  绑定参数

#### Scenario: guard 边单值退化

- **WHEN** 对一个 bridge 节点生成查询,且其 before_beans 仅含单个 bean_id
- **THEN** 生成的 IN 条件含且仅含一个绑定参数,查询语义正确

#### Scenario: 安全上限

- **WHEN** 以某个 limit 调用 build_expand_query
- **THEN** 生成的 SQL 含 LIMIT 子句,避免一次性拉取过多邻居

#### Scenario: 注入防护

- **WHEN** 起点节点某个 match 源列(含 guard 边拆分后的任一元素)的值含 SQL
  特殊字符
- **THEN** 该值作为绑定参数传入,查询语义不变,不发生注入
