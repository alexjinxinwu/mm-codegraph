## Context

mm-codegraph 项目将大型 Java/Spring 代码库的结构化知识存入 MySQL（schema 级隔离，每 schema 一套 14 表 ER 模型）。Claude Code 在代码生成时需要理解服务入口、流程编排、状态机、逻辑链与 Java 类型关系，但直接读源码/XML 效率低且易遗漏关联。

v1 已实现 `codegraph-mcp/codegraph-server.py`，作为 MCP Server 将图谱数据库暴露给 Claude Code。ER 关系文档见 `codegraph-mcp/ER.md`；初始化 SQL 见 `data/mmcodekg-init.sql`。

## Goals / Non-Goals

**Goals:**
- 通过 MCP 协议向 Claude Code 提供代码知识图谱的只读查询
- 封装 ER 关联：service_entry → flow/logic/bean、flow → state machine、chain → bridges → java_classes
- 支持跨 schema 多代码库（list_schemas + schema 参数）
- 提供关键字搜索与只读 SQL 兜底

**Non-Goals:**
- 图谱数据的写入、增量索引或 ETL（v1 范围外）
- HTTP/REST 对外暴露
- 认证鉴权层（依赖 MySQL 账号与网络隔离）
- 图谱可视化 UI

## Decisions

### 1. FastMCP + stdio transport
- **选择**: Python `mcp.server.fastmcp.FastMCP`，默认 stdio
- **理由**: Claude Code 原生支持 stdio MCP；单文件部署简单
- **替代**: HTTP MCP — 需额外进程管理与端口配置

### 2. 连接池与 schema 切换
- **选择**: DBUtils PooledDB + 每次查询 `USE \`schema\`` + 参数化 SQL
- **理由**: 多 schema 共享连接池；schema 名正则校验防注入
- **替代**: 每 schema 独立连接 — 资源浪费

### 3. 工具 API 设计（15 tools）

| 类别 | 工具 | 职责 |
|------|------|------|
| 导航 | list_schemas, schema_overview, search | 发现代码库与关键字定位 |
| 入口/流程 | find_service_entry, get_service_entry, get_flow, get_state, get_flow_statemachine | 服务入口与状态机 |
| 逻辑链 | resolve_chain | chain_id → steps/bridges/java_classes |
| Bean/Java | find_bean, find_class, get_class, find_method | 类型与方法查询 |
| 兜底 | sql_query | 只读 SELECT/WITH，自动 LIMIT |

### 4. 只读安全策略
- sql_query 仅允许单条 SELECT/WITH
- 正则拦截 insert/update/delete/drop 等关键字
- 无 LIMIT 时自动追加 LIMIT（默认 200）

### 5. 数据模型（14 表）
核心实体关系见 ER.md：service_entries 关联 flows/logics/beans；flows 展开 states/flow_tasks/activities/transitions；logics 展开 logic_steps/bridges 并关联 java_classes。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 默认连接凭据硬编码在代码中 | v2 改为纯环境变量、移除默认值 |
| 大结果集拖慢 MCP 响应 | 各工具默认 limit；sql_query 强制 LIMIT |
| schema 名注入 | `_schema()` 正则白名单校验 |
| 跨表 logic 关联为软关联（非 FK） | resolve_chain 显式解析 before_beans FQN |
| 索引滞后/数据过期 | 文档说明图谱为快照，非实时源码 |

## Migration Plan

1. 配置 Claude Code MCP：`codegraph-mcp/codegraph-server.py`（stdio）
2. 设置环境变量：MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD
3. 确保目标 schema 已通过 `data/mmcodekg-init.sql` 初始化并灌数
4. 调用 list_schemas → schema_overview 验证连通

回滚：从 Claude Code MCP 配置中移除该 server 即可，无状态副作用。

## Open Questions

- 是否在 v2 引入 requirements.txt 与 Docker 化部署
- 是否需要 MCP resources 暴露 ER 图文档
