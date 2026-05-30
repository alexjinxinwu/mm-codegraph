## Design Summary

Codegraph MCP Server（v1）将 MySQL 中的代码知识图谱以 MCP 工具形式暴露给 Claude Code，使 AI 助手在代码生成与分析时能结构化查询服务入口、流程状态机、逻辑链、Bean 与 Java 类/方法，而不依赖全文 grep 或人工翻 XML/Java 源码。

数据模型覆盖 14 张核心表（见 `codegraph-mcp/ER.md`），每张表对应代码库中某一维度的结构化抽取：service_entries、flows、states、activities、transitions、logics、logic_steps、bridges、beans、java_classes、java_methods、interceptors、flow_tasks、module_parameters。

MCP Server 采用 Python + FastMCP + PyMySQL 连接池，通过 stdio transport 接入 Claude Code；提供导航、领域查询与只读 SQL 兜底三类工具，共 15 个 MCP tool。

## Alternatives Considered

### Alternative A: 直接嵌入 SQL 到 Claude Code 系统提示
- **Approach**: 在 CLAUDE.md 中写死常用 SQL 模板，让模型自行拼查询
- **Pros**: 零额外进程；实现成本最低
- **Cons**: 无 schema 校验、无关联解析、易写错 JOIN；每次对话重复消耗 token
- **Why not chosen**: 无法封装领域语义（如状态机视图、逻辑链解析），维护成本高

### Alternative B: REST API 网关 + HTTP MCP
- **Approach**: 独立 Spring Boot 服务暴露 REST，MCP 层做 HTTP 代理
- **Pros**: 与现有 Java 技术栈一致；可复用 Spring 安全与监控
- **Cons**: 部署链路长；v1 只需只读查询，REST 层增加无谓复杂度
- **Why not chosen**: 首版目标是快速验证 Claude Code 集成，stdio MCP 更轻量

### Alternative C: MCP Server + 领域工具（Agreed Approach）
- **Approach**: Python FastMCP stdio server，按 ER 关系封装高层工具 + 只读 SQL 兜底
- **Pros**: 语义化 API（get_flow_statemachine、resolve_chain）；连接池复用；Claude Code 原生 MCP 集成
- **Cons**: 需维护 Python 依赖；跨 schema 多代码库需调用方传 schema 参数
- **Why chosen**: 平衡开发速度与查询表达能力，v1 已验证可用

## Agreed Approach

采用 Alternative C：独立 `codegraph-mcp/codegraph-server.py`，以 MCP tool 暴露代码图谱查询能力。每个 MySQL database（schema）对应一个已索引的代码库/代码组织；工具层负责关联跳转（入口→流程→状态机、逻辑链→Java 类），底层统一走连接池 + 参数化查询。

## Key Decisions

1. **传输层**: stdio（FastMCP 默认），适配 Claude Code MCP 配置
2. **数据访问**: PyMySQL + DBUtils PooledDB，环境变量配置连接（MYSQL_HOST/PORT/USER/PASSWORD/POOL_SIZE）
3. **安全**: 仅暴露 SELECT/WITH 只读查询；sql_query 工具拦截 DML/DDL 关键字
4. **工具分层**: 导航（list_schemas/search）→ 领域（flow/statemachine/chain/class）→ 兜底（sql_query）
5. **关联解析**: get_service_entry、resolve_chain、get_class 在单次调用内完成多表 JOIN 语义

## Open Questions

- v2 是否增加写入/增量索引接口（当前纯只读）
- 是否需要缓存热点 schema 的 overview 结果
- 多 schema 并行查询的并发限制策略
