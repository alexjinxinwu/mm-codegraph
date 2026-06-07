## 1. 节点模型(NodeSpec)

- [x] 1.1 注册全部 14 种节点类型,每种对应一张数据库表:
      service_entry, flow, logic, bean, state, flow_task, activity,
      transition, logic_step, bridge, java_class, interceptor,
      java_method, module_parameter
- [x] 1.2 为每种节点定义 NodeSpec:
      - id_column:行身份列,统一为 "id"(仅作唯一标识,不用于关联)
      - title:图上节点主标签字段
      - subtitle:图上节点次要标签字段
      落地值如下:
      | nodeType         | table             | title           | subtitle      |
      | service_entry    | service_entries   | name            | entry_type    |
      | flow             | flows             | flow_id         | flow_type     |
      | logic            | logics            | chain_id        | context_id    |
      | bean             | beans             | bean_id         | bean_class    |
      | state            | states            | state_name      | flow_id       |
      | flow_task        | flow_tasks        | task_type       | logic         |
      | activity         | activities        | activity_name   | activity_id   |
      | transition       | transitions       | trans_type      | next_target   |
      | logic_step       | logic_steps       | logic_type      | chain_id      |
      | bridge           | bridges           | bridge_id       | logic_type    |
      | java_class       | java_classes      | class_name      | package_name  |
      | interceptor      | interceptors      | stack_name      | bean_ref      |
      | java_method      | java_methods      | method_name     | class_fqn     |
      | module_parameter | module_parameters | parameter_name  | param_key     |
- [x] 1.3 提供按 nodeType 查 NodeSpec 的查找入口
- [x] 1.4 加载时校验:14 种类型全部存在,且每种 id_column / table 非空

## 2. forward 边规则(EDGE_RULES)

- [x] 2.1 定义 EdgeRule 结构:
      id、from、to、label、match(源列→目标列映射列表)、
      direction(本切片固定 out)、guard(仅 guard 边启用)
- [x] 2.2 编码 forward 平凡单列边(14 条):
      | id                       | from         | to          | match (src→dst)                  |
      | service_entry.flow       | service_entry| flow        | flow_id→flow_id                  |
      | service_entry.logic      | service_entry| logic       | chain_id→chain_id                |
      | service_entry.bean       | service_entry| bean        | bean_ref→bean_id                 |
      | flow.states              | flow         | state       | flow_id→flow_id                  |
      | flow.flow_tasks          | flow         | flow_task   | flow_id→flow_id                  |
      | flow.activities          | flow         | activity    | flow_id→flow_id                  |
      | flow.transitions         | flow         | transition  | flow_id→flow_id                  |
      | activity.transitions     | activity     | transition  | activity_id→activity_id          |
      | logic.logic_steps        | logic        | logic_step  | chain_id→chain_id                |
      | logic.bridges            | logic        | bridge      | chain_id→chain_id                |
      | logic_step.bridges       | logic_step   | bridge      | chain_id→chain_id                |
      | bean.java_class          | bean         | java_class  | bean_class→full_qualified_name   |
      | bean.interceptors        | bean         | interceptor | bean_id→bean_ref                 |
      | java_class.java_methods  | java_class   | java_method | full_qualified_name→class_fqn    |
- [x] 2.3 编码 forward 平凡复合键边(2 条,match 含两列):
      | id                  | from  | to         | match (src→dst)                                |
      | state.activities    | state | activity   | flow_id→flow_id, state_name→state_name         |
      | state.transitions   | state | transition | flow_id→flow_id, state_name→state_name         |
- [x] 2.4 编码 forward 语义边(2 条,列异名 + 显式假设标注):
      | id                  | from  | to         | match (src→dst)   | 标注                                  |
      | logic.activities    | logic | activity   | chain_id→logic    | 假设 activities.logic 存 chain_id,待校验 |
      | logic.flow_tasks    | logic | flow_task  | chain_id→logic    | 假设 flow_tasks.logic 存 chain_id,待校验 |
- [x] 2.5 编码 forward guard 边(1 条):
      | id            | from   | to   | match (src→dst)      | guard                                 |
      | bridge.beans  | bridge | bean | before_beans→bean_id | 按逗号拆分 before_beans 后逐项匹配 bean_id |
- [x] 2.6 校验每条规则的 from / to 都能在 NodeSpec 中找到,否则加载报错
- [x] 2.7 校验规则 id 全局唯一
- [x] 2.8 校验:被标记为 guard 类别的边必须带 guard 声明,否则加载报错
- [x] 2.9 提供「按 from 节点类型筛选 forward 边」的查找入口(含平凡/语义/guard 边)

## 3. forward 查询生成(build_expand_query)

- [x] 3.1 实现 build_expand_query(rule, node, limit),仅生成 forward join
- [x] 3.2 平凡边/语义边:对 rule.match 每一项生成「目标列 = 起点对应源列值」等值
      条件,多项以 AND 连接
- [x] 3.3 guard 边:按 guard 声明先将起点源列值拆分为列表,再生成「目标列 IN
      (绑定参数列表)」条件
- [x] 3.4 guard 边单值退化:源值仅含一项时生成含单个参数的 IN 条件
- [x] 3.5 起点节点各取值(含 guard 拆分后的每个元素)以绑定参数传入,不做字符串拼接
- [x] 3.6 生成的 SQL 含 LIMIT(由 limit 参数控制的安全上限)
- [x] 3.7 SELECT 列表覆盖目标 NodeSpec 的 id_column + title + subtitle 字段

## 4. 测试

- [x] 4.1 NodeSpec:任取一节点(如 flow)id_column 为 "id",title/subtitle 正确
- [x] 4.2 NodeSpec:14 种类型枚举齐全
- [x] 4.3 NodeSpec:按 nodeType 查找命中,未知类型返回空/报错
- [x] 4.4 NodeSpec:缺失 id_column / table 时加载报错
- [x] 4.5 EDGE_RULES:存在 service_entry→bean→java_class→java_method 的可达链
- [x] 4.6 EDGE_RULES:存在 flow→state→activity→transition 的可达链
- [x] 4.7 EDGE_RULES:logic→logic_step、logic→bridge 存在,且经 bridge→bean 接入
      bean 子树
- [x] 4.8 EDGE_RULES:语义边 logic→activity / logic→flow_task 的 match 为
      chain_id→logic,且带假设标注
- [x] 4.9 EDGE_RULES:guard 边 bridge→bean 的 match 为 before_beans→bean_id,
      且带拆分 guard 声明
- [x] 4.10 EDGE_RULES:from/to 引用不存在的节点类型时加载报错
- [x] 4.11 EDGE_RULES:重复规则 id 时加载报错
- [x] 4.12 EDGE_RULES:guard 类别边缺 guard 声明时加载报错
- [x] 4.13 build_expand_query:单列异名边(bean.java_class)SQL 快照正确,
      where 为 full_qualified_name = ?(绑定 bean_class 值)
- [x] 4.14 build_expand_query:复合键边(state.activities)where 同时约束
      flow_id 与 state_name 两列
- [x] 4.15 build_expand_query:语义边(logic.activities)where 为 logic = ?
      (绑定 chain_id 值)
- [x] 4.16 build_expand_query:guard 边(bridge.beans)多值时 where 为
      bean_id IN (?, ?, ...),元素逐个绑定
- [x] 4.17 build_expand_query:guard 边单值退化为含单参数的 IN
- [x] 4.18 build_expand_query:含 LIMIT
- [x] 4.19 build_expand_query:起点列值(含 guard 拆分元素)含 SQL 特殊字符时
      以参数绑定传入,查询语义不变