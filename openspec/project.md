# mm-codegraph

将大型 Java/Spring 代码库的结构化知识存入 MySQL 代码图谱，并通过 MCP 协议暴露给 Claude Code，用于 AI 辅助代码生成与分析。

## 技术栈

| 层 | 技术 |
|----|------|
| 代码图谱存储 | MySQL 8（schema 级隔离，14 表 ER 模型） |
| MCP Server | Python 3 + FastMCP + PyMySQL + DBUtils |
| AI 集成 | Claude Code（stdio MCP transport） |
| 规格驱动 | OpenSpec（Superspec schema） |

## 架构

```
MySQL 代码图谱 (14 表)     codegraph-mcp/codegraph-server.py     Claude Code
  service_entries  ──┐         15 MCP tools (只读)          ──→  代码生成/分析
  flows / states     ├──→  FastMCP stdio
  logics / bridges   │
  java_classes       ──┘
```

## 约定

- 每个 MySQL database schema 对应一个已索引的代码库
- MCP 查询 MUST 为只读（SELECT/WITH），写操作不在 v1 范围
- ER 关系真源：`codegraph-mcp/ER.md`
- 新能力先走 OpenSpec 变更流程（`/opsx:new` → `/opsx:apply` → `/opsx:archive`）

## 已实现能力

| Capability | 说明 | Spec |
|------------|------|------|
| codegraph-mcp | MCP Server 暴露代码知识图谱查询（v1，15 tools） | `openspec/specs/codegraph-mcp/spec.md` |
| graph-core | ER 图模型内核（NodeSpec、EDGE_RULES、build_expand_query） | `openspec/specs/graph-core/spec.md` |
| graph-api | HTTP 图探索 API（GET /api/v1/resolve、POST /api/v1/expand） | `openspec/specs/graph-api/spec.md` |
| browser-ui | 浏览器外壳与入口搜索（React SPA，消费 /resolve） | `openspec/specs/browser-ui/spec.md` |
| propose-migration-skill | 输入 commandId/flowId，调用 `search_service_impact` 在 codeBaseRoot 写出 `<id>-plan.txt` | `openspec/specs/propose-migration-skill/spec.md` |

## 相关文档

- ER 模型：`codegraph-mcp/ER.md`
- MCP 实现：`codegraph-mcp/codegraph-server.py`
- Superspec 工作流：`openspec/schemas/superspec/INTEGRATION.md`
- Claude Code 说明：`CLAUDE.md`
