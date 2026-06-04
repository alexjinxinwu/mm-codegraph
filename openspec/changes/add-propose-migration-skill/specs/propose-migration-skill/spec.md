# propose-migration-skill

## Purpose

在 Claude Code 中以一条 slash 命令的形式，封装 mm-codegraph MCP 的 `search_service_impact`：接收一个 `commandId` 或 `flowId` 作为输入，自动补全默认 schema (`1_0_baseline`) 与 `codeBaseRoot`，调用 MCP 工具拿到受影响文件集合，并在 `codeBaseRoot` 根目录写出 `<id>-plan.txt`，供迁移方案制定直接消费。

## Requirements

### Requirement: Skill 入口与触发
系统 SHALL 提供名为 `propose-migration` 的 Claude Code skill，注册在 `.claude/skills/propose-migration/SKILL.md`。用户通过 `/propose-migration <commandId|flowId>` 触发；当 `<id>` 同时存在同名 commandId 和 flowId 时，skill MUST 优先按 commandId 处理，并在输出中显式说明被选中的是哪一类。

#### Scenario: 通过 commandId 触发
- **WHEN** 用户执行 `/propose-migration ReleaseOrgOperatorCCSuspendStatus`
- **THEN** skill 调用 `mcp__mm-codegraph__search_service_impact` 并传 `commandId="ReleaseOrgOperatorCCSuspendStatus"`
- **THEN** 不再额外传 `flowId`

#### Scenario: 通过 flowId 触发
- **WHEN** 用户执行 `/propose-migration <flowId>` 且与 `service_entries` 中无同名 commandId
- **THEN** skill 调用 `search_service_impact` 并传 `flowId=<flowId>`
- **THEN** 不再额外传 `commandId`

### Requirement: 默认参数与 codeBaseRoot 兜底
skill MUST 始终向 `search_service_impact` 传递 `schema="1_0_baseline"`，除非用户在参数中显式以 `schema=<name>` 前缀覆盖。`codeBaseRoot` MUST 优先取用户传入的 `--codebase=<path>`，其次取环境变量 `MM_CODEGRAPH_CODEBASE_ROOT`，再次取当前 shell 工作目录的探测值；若三者皆无，skill MUST 在响应中明确提示"未配置 codeBaseRoot，将跳过 resources/namingsql 等资源类扫描"再继续执行，且不得静默失败。

#### Scenario: 显式 schema 与 codeBaseRoot
- **WHEN** 用户执行 `/propose-migration --schema=2_1_release ReleaseOrgOperatorCCSuspendStatus --codebase=D:/2026/MobileMoneyMonorepo`
- **THEN** 调用 `search_service_impact` 时 `schema="2_1_release"`、`commandId="ReleaseOrgOperatorCCSuspendStatus"`、`codeBaseRoot="D:/2026/MobileMoneyMonorepo"`

#### Scenario: 走默认与 env 兜底
- **WHEN** 用户执行 `/propose-migration ReleaseOrgOperatorCCSuspendStatus`，环境变量 `MM_CODEGRAPH_CODEBASE_ROOT=D:/2026/MobileMoneyMonorepo` 已设置
- **THEN** 调用参数为 `schema="1_0_baseline"`、`commandId="ReleaseOrgOperatorCCSuspendStatus"`、`codeBaseRoot="D:/2026/MobileMoneyMonorepo"`

### Requirement: 文件输出契约
skill MUST 在成功收到 MCP 返回后，向 `codeBaseRoot` 根目录写出一个纯文本文件，文件名为 `<id>-plan.txt`（`<id>` 即用户传入的原始 commandId 或 flowId，未做大小写/分隔符转换）。文件 MUST 为 UTF-8 编码、首行保留 schema 元信息 `# schema: <schema>`，之后每行一条受影响的源文件绝对路径，按字典序升序排列、去除重复与空行。

#### Scenario: commandId 落盘为 commandId-plan.txt
- **WHEN** `/propose-migration ReleaseOrgOperatorCCSuspendStatus` 在 `codeBaseRoot=D:/2026/MobileMoneyMonorepo` 下完成
- **THEN** 文件 `D:/2026/MobileMoneyMonorepo/ReleaseOrgOperatorCCSuspendStatus-plan.txt` 存在
- **THEN** 首行 `# schema: 1_0_baseline`，其后按字典序列出所有受影响文件绝对路径

#### Scenario: flowId 落盘为 flowId-plan.txt
- **WHEN** `/propose-migration <flowId>` 完成
- **THEN** 输出文件名为 `<flowId>-plan.txt`，位置同样在 `codeBaseRoot` 根目录

#### Scenario: 输出目录不存在
- **WHEN** `codeBaseRoot` 路径不存在或不是目录
- **THEN** skill MUST 拒绝写盘并向用户报错，错误信息包含 `codeBaseRoot` 的实际取值与"路径不存在或不可访问"原文

### Requirement: 错误处理与可观测性
当 `search_service_impact` 返回非空 `error` 字段、或 HTTP/网络层失败、或返回的受影响文件集合为空时，skill MUST 仍写出 `<id>-plan.txt`，但首行需在 schema 元信息后追加状态行 `# status: <ok|empty|error>` 与 `# reason: <text>`，避免出现"用户以为跑成功了但其实失败"的盲区。

#### Scenario: MCP 返回错误
- **WHEN** `search_service_impact` 返回 `{"error": "<msg>"}`
- **THEN** 仍创建 `<id>-plan.txt`，包含 `# status: error` 与 `# reason: <msg>`，文件正文为空
- **THEN** skill 在回复中 MUST 把该 reason 原样呈现给用户

#### Scenario: 影响集为空
- **WHEN** `search_service_impact` 返回的影响文件集合为 0 条
- **THEN** 仍创建 `<id>-plan.txt`，包含 `# status: empty` 与 `# reason: no affected files found`
- **THEN** 不视为失败，正常结束

### Requirement: 依赖声明
skill 的 SKILL.md MUST 在 frontmatter 或首段说明：本 skill 依赖 mm-codegraph MCP server (`codekg`) 已在 Claude Code 中注册；如未注册，skill 必须在第一次调用时输出明确指引（包含配置文件路径与 `codegraph-mcp/codegraph-server.py` 启动命令）后再退出。

#### Scenario: MCP 未注册
- **WHEN** 环境中无 `mcp__mm-codegraph__search_service_impact` 工具
- **THEN** skill 不静默执行；回复中 MUST 给出 MCP 注册示例与如何启动 `codegraph-server.py`
