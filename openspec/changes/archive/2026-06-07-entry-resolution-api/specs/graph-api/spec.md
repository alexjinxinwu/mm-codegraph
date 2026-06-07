## ADDED Requirements

### Requirement: 入口解析注册表

系统 SHALL 以声明式 ENTRY_RESOLVERS 注册表表达各种外部标识到根节点的解析方式。
每个 EntryResolver 至少声明 kind、目标 nodeType、以及把外部 value 转为参数化查询
所需的目标表与匹配列。新增入口种类 MUST 只需往注册表加规则,不改端点逻辑。

本能力 SHALL 至少注册:kind=commandId(解析到 service_entries)与 kind=flowId
(解析到 flows)。

#### Scenario: resolver 引用的节点类型必须存在

- **WHEN** 加载 ENTRY_RESOLVERS
- **THEN** 每个 resolver 的 nodeType 都能在 graph-core 找到对应 NodeSpec,
  否则加载报错

#### Scenario: 注册两种内置入口

- **WHEN** 枚举已注册 resolver
- **THEN** 至少含 kind=commandId 与 kind=flowId

### Requirement: 入口解析端点

系统 SHALL 提供 GET /resolve?schema=&kind=&value=,按 kind 选定 resolver,将
value 解析为 graph-core 根节点。解析结果中的节点 MUST 用目标 NodeSpec 整形为
{ type, id, title, subtitle },其形态与 /expand 的节点一致,可不加转换地作为
/expand 的输入。

#### Scenario: commandId 唯一命中

- **WHEN** 提交 schema=S&kind=commandId&value=C1 且存在唯一匹配
- **THEN** status 为 found
- **AND** roots 含一个 type 为 service_entry 的节点

#### Scenario: flowId 唯一命中

- **WHEN** 提交 schema=S&kind=flowId&value=F1 且存在唯一匹配
- **THEN** status 为 found
- **AND** roots 含一个 type 为 flow 的节点

#### Scenario: 根节点可直接用于展开

- **WHEN** 解析返回任一根节点或候选节点
- **THEN** 该节点含 type 与 id,满足 /expand 的输入要求,无需转换

### Requirement: 解析三态语义

系统 SHALL 区分无命中、唯一命中、多命中三种结果,并以统一结构返回。多命中
时 SHALL 返回全部候选供前端消歧,而非任意取一。

#### Scenario: 无命中

- **WHEN** value 在目标表查无匹配
- **THEN** status 为 notFound,roots 与 candidates 均为空
- **AND** HTTP 层不视为错误

#### Scenario: 多命中待消歧

- **WHEN** 同一 value 命中多行(如一个 flowId 对应多个候选根)
- **THEN** status 为 multiple,candidates 列出全部命中节点,roots 为空

#### Scenario: 唯一命中

- **WHEN** value 恰好命中一行
- **THEN** status 为 found,roots 含该节点,candidates 为空

### Requirement: 解析输入校验与注入防护

系统 SHALL 在查询数据库前完成输入校验,并对外部 value 参数化绑定。

#### Scenario: 未知 kind

- **WHEN** kind 不是任何已注册 resolver
- **THEN** 返回校验错误,不查数据库

#### Scenario: 非法 schema

- **WHEN** schema 不在允许列表内
- **THEN** 返回校验错误,不查数据库

#### Scenario: value 缺失

- **WHEN** 未提供 value 或 value 为空
- **THEN** 返回校验错误,不查数据库

#### Scenario: 注入防护

- **WHEN** value 含 SQL 特殊字符
- **THEN** 以绑定参数传入,查询语义不变