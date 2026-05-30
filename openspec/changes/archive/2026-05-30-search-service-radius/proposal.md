## Why

开发人员在进行代码变更前，往往需要手动跨表查询 service_entries → flows → states → transitions → logics → bridges → beans，才能了解"如果我改了这个服务，会影响哪些文件"。这个过程：
1. 效率低——需要记忆复杂的 ER 关系
2. 易遗漏——多层递归容易漏掉某些路径
3. 无法自动化——无法集成到 CI/CD 流程中

通过提供 `search_service_impact` MCP tool，可以将上述手工查询自动化，输出受影响文件列表，支持变更影响分析、测试用例推荐等下游场景。

## What Changes

**新增 MCP tool：**
- 函数名: `search_service_impact`
- 功能：通过 `commandId` 或 `flowId` 搜索服务影响范围
- 参数：`schema`（数据库）、`commandId`（可选）、`flowId`（可选）、`direction`（forward/backward/both）、`maxDepth`（最大深度）
- 输出：受影响文件列表（含 Java 源文件和 XML 配置）及完整调用链

**新增代码：**
- 在 `codegraph-mcp/codegraph-server.py` 新增 `search_service_impact` 函数
- BFS 遍历逻辑内嵌于函数内部

**数据层变更：**
- 复用现有 MySQL schema 的 13 张表
- 无表结构变更

## Capabilities

### New Capabilities
- `impact-search-api`: 提供基于 ER 关系的服务影响搜索 MCP tool，支持双向遍历和深度控制

### Modified Capabilities
- （无）

## Impact

**代码：**
- 修改 `codegraph-mcp/codegraph-server.py`，新增 `search_service_impact` 函数

**依赖：**
- 复用现有 `1.0_Base` schema 的 13 张表
- 无新增外部依赖

**测试：**
- 单元测试：验证 BFS 遍历路径（正向、反向、环路检测）
- 集成测试：调用 `search_service_impact` 验证返回结果
