## Why

当前 mm-codegraph MCP 提供的 `search_service_impact` 工具虽能完整计算某个 commandId / flowId 的影响面（13 表 ER + 启发式 + 资源扫描），但每次都得手写 prompt、记 schema 名（`1_0_baseline`）、传 `codeBaseRoot`，再把结果贴到项目目录里。**产出一条可被迁移执行直接消费的"受影响文件清单"** —— 包含 `<id>-plan.txt` 的命名规范、固定的输出位置、按绝对路径写盘 —— 是把图谱能力落到迁移工作流的关键拼图。没有它，迁移方案制定者在"分析 → 计划"之间要手工转一道 5 字段的 tool call，重复且易错（最常见的就是忘传 `codeBaseRoot` 漏掉 namingsql 资源）。

## What Changes

**propose-migration 用户面 skill**
- **From**：手动调用 `mcp__mm-codegraph__search_service_impact`，自己组合 `commandId`/`flowId`、`schema=1_0_baseline`、`codeBaseRoot`、处理返回的复杂 JSON
- **To**：一句 `/propose-migration <commandId|flowId>`，由 skill 把 MCP 调用 + 路径规划 + 文件写出全包办
- **Reason**：降低从"想分析"到"拿到可读文件清单"的摩擦；固化已知约定（默认 schema、命名规则、codeBaseRoot 兜底）防止漏传
- **Impact**：新增；纯加法。codegraph-mcp 的 15 个 tool 不变。

**文件输出契约**
- 输入为 `commandId` 时：`{codeBaseRoot}/<commandId>-plan.txt`
- 输入为 `flowId` 时：`{codeBaseRoot}/<flowId>-plan.txt`
- 文件内容为受影响的源文件绝对路径列表（每行一条；头部保留 1 行 schema 元信息）

**新增 capability `propose-migration-skill`**，与现有 `codegraph-mcp` capability 互补：前者是 MCP 工具集合（数据访问层），后者是封装该工具的 slash skill（用户交互层）。

## Capabilities

### New Capabilities
- `propose-migration-skill`: 基于 mm-codegraph MCP 的 `search_service_impact` 提供"输入 commandId/flowId → 输出受影响文件清单"的端到端 slash skill

### Modified Capabilities
- （无）

## Impact

- **新增 skill**：`.claude/skills/propose-migration/SKILL.md`（skill 入口；本变更唯一新增文件）
- ~~新增脚本 `scripts/propose_migration.py`~~：取消（详见 `design.md` 决策 1）
- **受影响 MCP tool**：`mcp__mm-codegraph__search_service_impact`（仅作为依赖被调用，自身零修改）
- **配置 / 文档**：
  - `.claude/skills/propose-migration/SKILL.md` 顶部说明依赖 `codegraph-mcp` MCP server 已注册
  - 第一次使用若未配 `codeBaseRoot`，skill 会主动提示而非静默走 `os.walk` 之外的路径
- **回退**：删除 skill 目录即可，无外部副作用；产出的 `<id>-plan.txt` 是普通文本，可手动编辑/删除
