# Graph API

## Purpose

在 `codegraph-server` 暴露 HTTP 图探索 API：将外部标识解析为根节点，再逐层展开 ER 图邻居。

| 端点 | 说明 |
|------|------|
| **GET `/api/v1/resolve`** | `?schema=&kind=&value=` → `{ status, roots, candidates }`（三态：notFound / found / multiple） |
| **POST `/api/v1/expand`** | `{ schema, node: { type, id }, edgeIds? }` → `{ nodes, edges }` |

resolve 编排：`resolve_entry` → ENTRY_RESOLVERS → `QueryEngine.q()`。expand 编排：`expand_neighbors` → 水合 → `build_expand_query` → `QueryEngine.q()`。

实现位置：`codegraph_core/graph/`（`entry_resolvers.py`、`resolve_service.py`、`expand_service.py`）、`codegraph_server/routes.py`、`schemas_resolve.py`、`schemas_expand.py`。

## Requirements

### Requirement: 节点展开端点

系统 SHALL 提供 POST /api/v1/expand,输入一个起点节点与可选 edgeIds,返回该节点沿
forward ER 边得到的直接邻居,作为可增量合并的 { nodes, edges }。展开 MUST 由
graph-core 的 EDGE_RULES 驱动,SQL MUST 由 build_expand_query 生成。

请求体形如 { schema, node: { type, id }, edgeIds? }。返回的 nodes MUST 携带
type 与 id,使其可直接作为下一次 /expand 的输入并供前端去重。

#### Scenario: 默认展开全部适用 forward 边

- **WHEN** 提交 { schema: "S", node: { type: "flow", id: 10 } } 且不带 edgeIds
- **THEN** 返回该 flow 沿所有 from 为 flow 的 forward 边的邻居
- **AND** edges 中每条含 ruleId、from、to、label

#### Scenario: 仅展开指定边

- **WHEN** 提交 edgeIds: ["flow.states"]
- **THEN** 仅返回 flow.states 边的邻居,其余 from 为 flow 的边不展开

#### Scenario: 邻居节点可直接再次展开

- **WHEN** 展开成功返回若干邻居节点
- **THEN** 每个节点含 type 与 id,可不加转换地作为下一次 /expand 的 node 输入

---

### Requirement: 起点节点水合

由于 NodeSpec 的 id 仅作行身份、边的关联建立在业务列上,系统在执行展开前 SHALL
按起点 node.id 从其对应表水合出该行,取得 forward 边规则所需的业务源列值,再交给
build_expand_query。客户端无需提供 join 列。

#### Scenario: 异名列关联

- **WHEN** 对 { type: "bean", id: 5 } 按 bean.java_class 展开
- **THEN** 服务端先水合该 bean 行取得 bean_class 值
- **AND** 查询 java_classes 中 full_qualified_name 等于该 bean_class 值的行

#### Scenario: 复合键关联

- **WHEN** 对 { type: "state", id: 7 } 按 state.activities 展开
- **THEN** 水合该 state 行取得 flow_id 与 state_name
- **AND** 查询同时以 flow_id 与 state_name 两列约束

#### Scenario: 语义边关联

- **WHEN** 对 { type: "logic", id: 3 } 按 logic.activities 展开
- **THEN** 水合取得 chain_id 值,查询 activities 中 logic 列等于该值的行

#### Scenario: guard 边关联

- **WHEN** 对 { type: "bridge", id: 2 } 按 bridge.beans 展开
- **THEN** 水合取得 before_beans 值,按逗号拆分后查询 bean_id IN 拆分结果的 beans

#### Scenario: 起点不存在

- **WHEN** node.id 在对应表中查无此行
- **THEN** 返回空 nodes 与空 edges,HTTP 层不视为错误

---

### Requirement: 结果去重与安全上限

系统 SHALL 对返回的节点按 (type, id) 去重、对边按 (ruleId, fromId, toId) 去重,
并对每条边的邻居数施加硬编码安全上限。

#### Scenario: 节点去重

- **WHEN** 多条 forward 边指向同一目标 (type, id)
- **THEN** 该节点在 nodes 中仅出现一次,但每条命中的边各自保留在 edges 中

#### Scenario: 安全上限

- **WHEN** 某条边的邻居数超过上限
- **THEN** 仅返回上限内的邻居,响应不报错

---

### Requirement: 展开输入校验与注入防护

系统 SHALL 在查询数据库前完成输入校验,并对所有取值参数化绑定。

#### Scenario: 非法节点类型

- **WHEN** 提交不在 14 种已知类型内的 nodeType
- **THEN** 返回校验错误,不查数据库

#### Scenario: 非法 schema

- **WHEN** schema 不在允许列表内
- **THEN** 返回校验错误,不查数据库

#### Scenario: edgeId 与节点类型不匹配

- **WHEN** edgeIds 含一条 from 不等于 node.type 的规则 id,或含未注册的 id
- **THEN** 返回校验错误,不查数据库

#### Scenario: 注入防护

- **WHEN** node.id 或水合得到的源列值含 SQL 特殊字符
- **THEN** 以绑定参数传入,查询语义不变

---

### Requirement: 入口解析注册表

系统 SHALL 以声明式 ENTRY_RESOLVERS 注册表表达各种外部标识到根节点的解析方式。
每个 EntryResolver 至少声明 kind、目标 nodeType、以及把外部 value 转为参数化查询
所需的目标表与匹配列。新增入口种类 MUST 只需往注册表加规则,不改端点逻辑。

本能力 SHALL 至少注册:kind=commandId(解析到 service_entry)与 kind=flowId
(解析到 flow)。

#### Scenario: resolver 引用的节点类型必须存在

- **WHEN** 加载 ENTRY_RESOLVERS
- **THEN** 每个 resolver 的 nodeType 都能在 graph-core 找到对应 NodeSpec,
  否则加载报错

#### Scenario: 注册两种内置入口

- **WHEN** 枚举已注册 resolver
- **THEN** 至少含 kind=commandId 与 kind=flowId

---

### Requirement: 入口解析端点

系统 SHALL 提供 GET /api/v1/resolve?schema=&kind=&value=,按 kind 选定 resolver,将
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

---

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

---

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
