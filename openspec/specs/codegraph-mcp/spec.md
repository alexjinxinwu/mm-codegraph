# Codegraph MCP

## Purpose

通过 MCP 协议向 Claude Code 暴露 MySQL 代码知识图谱的只读查询能力。每个 MySQL database schema 对应一个已索引的代码库，数据模型为 14 表 ER 关系（见 `codegraph-mcp/ER.md`）。MCP Server 实现位于 `codegraph-mcp/codegraph-server.py`。

## Requirements

### Requirement: MCP Server 注册与传输
系统 SHALL 提供基于 FastMCP 的 MCP Server（`codegraph-mcp/codegraph-server.py`），使用 stdio transport，服务名称为 `codekg`，供 Claude Code 通过 MCP 配置接入。

#### Scenario: Claude Code 启动 MCP Server
- **WHEN** Claude Code 按 stdio 方式启动 codegraph-server.py
- **THEN** MCP Server 初始化连接池并注册全部查询工具
- **THEN** Server 通过 stdio 响应 MCP 协议请求

---

### Requirement: Schema 导航
系统 SHALL 提供 schema 级导航工具，使调用方能发现可用代码库并了解数据规模。

#### Scenario: 列出所有代码图谱 schema
- **WHEN** 调用 `list_schemas`
- **THEN** 返回 MySQL 实例上除系统库外的全部 database 名称列表

#### Scenario: 查看 schema 表行数概览
- **WHEN** 调用 `schema_overview` 并传入合法 schema 名
- **THEN** 返回该 schema 下 14 张核心表各自的行数统计

#### Scenario: 跨表关键字搜索
- **WHEN** 调用 `search` 并传入 schema 与 keyword
- **THEN** 在 service_entries、flows、beans、java_classes 中模糊匹配并返回分组结果

---

### Requirement: 服务入口与流程状态机查询
系统 SHALL 提供服务入口、流程、状态及完整状态机视图的结构化查询，并自动解析 ER 关联。

#### Scenario: 查找服务入口
- **WHEN** 调用 `find_service_entry` 并传入 schema 与可选 keyword
- **THEN** 按 name/uri/command_id/business_type 模糊匹配返回 service_entries 记录

#### Scenario: 获取入口关联详情
- **WHEN** 调用 `get_service_entry` 并传入 schema 与 name
- **THEN** 返回匹配的 service_entries 及其关联的 flow、logic、bean 记录

#### Scenario: 获取流程与状态列表
- **WHEN** 调用 `get_flow` 并传入 schema 与 flow_id
- **THEN** 返回 flows 基本信息、按 state_order 排序的 states、按 task_order 排序的 flow_tasks

#### Scenario: 获取单状态 activities 与 transitions
- **WHEN** 调用 `get_state` 并传入 schema、flow_id、state_name
- **THEN** 返回该状态下的 activities（含 logic）与 transitions

#### Scenario: 构建完整状态机视图
- **WHEN** 调用 `get_flow_statemachine` 并传入 schema 与 flow_id
- **THEN** 返回按 state_order 排列的状态机结构，每个 state 包含其 activities 与 transitions

---

### Requirement: 逻辑链解析
系统 SHALL 支持按 chain_id 解析逻辑链，并将 bridges.before_beans 解析为 java_classes 记录。

#### Scenario: 解析逻辑链及关联 Java 类
- **WHEN** 调用 `resolve_chain` 并传入 schema 与 chain_id
- **THEN** 返回 logics、logic_steps、bridges 记录
- **THEN** 将 bridges 中逗号/分号分隔的 before_beans FQN 解析为 java_classes 条目（class_name、full_qualified_name、file_path、semantic）

---

### Requirement: Bean 与 Java 类型查询
系统 SHALL 提供 Bean、Java 类与方法的结构化查询，支持继承/实现关系与语义字段。

#### Scenario: 模糊查找 Bean
- **WHEN** 调用 `find_bean` 并传入 schema 与 keyword
- **THEN** 按 bean_id 或 bean_class 模糊匹配返回 beans 记录

#### Scenario: 查找 Java 类
- **WHEN** 调用 `find_class` 并传入 schema、keyword 及 exact 标志
- **THEN** exact=True 时按 full_qualified_name 精确匹配；否则按 class_name/FQN 模糊匹配

#### Scenario: 获取类完整信息
- **WHEN** 调用 `get_class` 并传入 schema 与 fqn
- **THEN** 返回类完整信息（含 semantic、注解、继承/实现）
- **THEN** 当 include_methods=True 时一并返回 methods、subclasses、implementors、beans

#### Scenario: 查找 Java 方法
- **WHEN** 调用 `find_method` 并传入 schema 及可选 method_name、class_fqn
- **THEN** 按条件过滤返回 java_methods 记录（含 full_signature、modifiers、annotations）

---

### Requirement: 只读 SQL 兜底与安全约束
系统 SHALL 提供只读 SQL 查询兜底，并 MUST 拒绝一切写操作与多语句执行。

#### Scenario: 执行合法只读查询
- **WHEN** 调用 `sql_query` 并传入 schema 与单条 SELECT 或 WITH 语句
- **THEN** 在指定 schema 执行查询并返回 JSON 格式结果
- **THEN** 若语句无 LIMIT 则自动追加 LIMIT（默认 200）

#### Scenario: 拒绝非只读或多语句
- **WHEN** 调用 `sql_query` 传入含 INSERT/UPDATE/DELETE/DROP 等关键字的语句，或含多条语句（分号分隔）
- **THEN** 系统 MUST 抛出 ValueError 并拒绝执行

#### Scenario: Schema 名安全校验
- **WHEN** 任意工具接收含非法字符的 schema 参数
- **THEN** 系统 MUST 拒绝执行并返回非法 schema 名错误

---

### Requirement: 数据库连接配置
系统 SHALL 通过环境变量配置 MySQL 连接，并使用连接池管理连接。

#### Scenario: 环境变量覆盖默认连接
- **WHEN** 设置 MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_POOL_SIZE 环境变量
- **THEN** 连接池 MUST 使用环境变量值建立连接
- **THEN** 各查询工具共享同一连接池实例

---

### Requirement: 代码知识图谱 ER 模型
系统所查询的数据 MUST 遵循 `codegraph-mcp/ER.md` 定义的 14 表模型及关联关系。

#### Scenario: 核心表覆盖
- **WHEN** schema_overview 或领域查询工具访问数据
- **THEN** 数据 MUST 来自以下表之一：service_entries、flows、states、flow_tasks、activities、transitions、logics、logic_steps、bridges、beans、java_classes、java_methods、interceptors、module_parameters

#### Scenario: ER 关联一致性
- **WHEN** get_service_entry 解析入口关联
- **THEN** flow 关联 MUST 通过 service_entries.flow_id → flows.flow_id
- **THEN** logic 关联 MUST 通过 service_entries.chain_id → logics.chain_id
- **THEN** bean 关联 MUST 通过 service_entries.bean_ref → beans.bean_id
