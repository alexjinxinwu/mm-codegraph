## 1. MCP Server 骨架与连接层

- [x] 1.1 创建 `codegraph-mcp/codegraph-server.py`，初始化 FastMCP（服务名 codekg）
- [x] 1.2 实现 PyMySQL + DBUtils PooledDB 连接池，支持环境变量配置
- [x] 1.3 实现 schema 名白名单校验与参数化查询辅助函数 `q()`

## 2. 导航类工具

- [x] 2.1 实现 `list_schemas`：列出非系统 database
- [x] 2.2 实现 `schema_overview`：14 表行数统计
- [x] 2.3 实现 `search`：跨 service_entries/flows/beans/java_classes 关键字搜索

## 3. 入口 / 流程 / 状态机工具

- [x] 3.1 实现 `find_service_entry` 与 `get_service_entry`（含 flow/logic/bean 关联解析）
- [x] 3.2 实现 `get_flow`：flow + states + flow_tasks
- [x] 3.3 实现 `get_state`：activities + transitions
- [x] 3.4 实现 `get_flow_statemachine`：完整状态机视图

## 4. 逻辑链与 Java 类型工具

- [x] 4.1 实现 `resolve_chain`：logics/steps/bridges + before_beans → java_classes
- [x] 4.2 实现 `find_bean`、`find_class`、`get_class`、`find_method`

## 5. 安全兜底与文档

- [x] 5.1 实现 `sql_query` 只读约束（单语句 SELECT/WITH、关键字拦截、自动 LIMIT）
- [x] 5.2 编写 `codegraph-mcp/ER.md` 14 表 ER 关系文档

## 6. Claude Code 集成验证

- [x] 6.1 确认 stdio transport 可启动并响应 MCP 工具列表
- [x] 6.2 对目标 schema 执行 list_schemas → schema_overview → search 冒烟验证
