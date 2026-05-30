## Why

Claude Code 在大型 Java/Spring 代码库中做代码生成与分析时，缺乏对服务入口、流程状态机、逻辑链与 Java 类型关系的结构化感知，只能依赖 grep 或人工阅读 XML/Java 源码，效率低且易遗漏跨文件关联。项目已将代码知识抽取为 MySQL 图谱（14 表 ER 模型），需要通过 MCP 协议将该图谱暴露给 AI 助手，使查询具备领域语义而非裸 SQL。

## What Changes

- 新增 `codegraph-mcp/codegraph-server.py`：基于 FastMCP 的 MCP Server（stdio transport）
- 新增 `codegraph-mcp/ER.md`：代码知识图谱 14 表 ER 关系文档
- 提供 15 个 MCP tool，覆盖 schema 导航、服务入口/流程/状态机、逻辑链、Bean/Java 类方法查询及只读 SQL 兜底
- 连接 MySQL 代码图谱库，每 database schema 对应一个已索引代码库

## Capabilities

### New Capabilities
- `codegraph-mcp`: 通过 MCP 协议向 Claude Code 暴露 MySQL 代码知识图谱的只读查询能力，含领域语义工具与安全约束

### Modified Capabilities
- （无）

## Impact

- **新增代码**: `codegraph-mcp/codegraph-server.py`、`codegraph-mcp/ER.md`
- **依赖**: Python 3、 pymysql、dbutils、mcp（FastMCP）
- **基础设施**: 需可访问的 MySQL 实例及已灌数的代码图谱 schema
- **Claude Code 配置**: 需注册 MCP server 指向 codegraph-server.py
- **数据**: 只读访问，不影响图谱写入链路
