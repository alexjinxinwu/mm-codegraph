## Context

- mm-codegraph MCP 已经在 Claude Code 侧以 `codekg` 名字注册（见 `codegraph-mcp/codegraph-server.py`），通过 stdio transport 暴露 15 个只读工具。其中 `search_service_impact` 是 13 表 ER 遍历 + 启发式 + 资源扫描的复合分析入口，但它的成功依赖 4 个必要入参：schema、commandId/flowId（二选一）、`codeBaseRoot`（强烈建议传，否则漏掉 namingsql）。
- 当前记忆里已经有一条 feedback：调用 `search_service_impact` 漏传 `codeBaseRoot` 是个真实踩过的坑（`feedback_search_service_impact_must_pass_codebaseroot.md`）。这正是 skill 想要从体验上根除的失败模式。
- 用户的需求形态固定为："一个 slash 命令，输入一个 id，输出一个文件"，非常像 OpenSpec 里"一个封装型 skill"的标准模式 —— skill 本身不引入新数据源，只决定何时调、调完后文件写哪里、写什么格式。

## Goals / Non-Goals

**Goals:**
- 一条 `/propose-migration <id>` 命令端到端走通：参数解析 → MCP 调用 → 字典序去重 → 落盘
- 把"`codeBaseRoot` 容易漏"这一已知的失败模式从用户视野中抹掉；让缺失变为显式提示
- 输出 `<id>-plan.txt` 格式稳定、可被后续迁移 plan 工具直接消费（首行 schema 元信息 + 字典序绝对路径）
- 错误/空集不静默：必落盘并带 status 行

**Non-Goals:**
- 不重新实现 `search_service_impact` 的遍历算法
- 不引入新的 MCP tool；纯消费 `mcp__mm-codegraph__search_service_impact`
- 不做结果可视化（不写 JSON、不画图）
- 不支持批量输入（一次一个 id；批量留给将来的 batch-skill）

## Decisions

### 1. Skill 形态：纯 SKILL.md，由 LLM 调 MCP + Write 落盘
- **Why**：Claude Code 平台下，调用 `mcp__mm-codegraph__search_service_impact` 与 `Write` 工具本身就是 LLM 的本职。让 SKILL.md 给出确定性的指令序列（参数模板 → 调 MCP → 解析 → 字典序去重 → 写文件），LLM 沿指令执行即可；契约写在前置 prompt 阶段，不在外部脚本里。这避免了"再实现一遍 stdio JSON-RPC 客户端"与"LLM 既要执行 skill 又要把 token 给独立脚本"的双重开销。
- **Alternative considered**：独立 Python 脚本走 stdio 调 `codegraph-server.py`。否决：在 Claude Code 会话内 MCP 已被运行时管理，脚本路径只能给 CI/批处理用，本变更用户场景不在此。保留为非目标。

### 2. 默认 `schema="1_0_baseline"` 写死在前缀解析中
- **Why**：用户的需求明确写"默认 schema 是 1_0_baseline"，这是仓库当前唯一的代码库，未来切库要显式覆盖。
- **Alternative considered**：把默认 schema 做成 skill 内的可配置常量、并通过环境变量覆盖。否决：当前没有第二个 schema 索引，预加一层抽象属于 [[feedback_premature-abstraction]]。

### 3. `codeBaseRoot` 三级兜底顺序：CLI flag > env > 工作目录探测
- **Why**：和用户既有的 CLAUDE.md "MM_CODEGRAPH_CODEBASE_ROOT" 约定一致；既能从单次调用覆盖，又能沿用全局默认。
- **Alternative considered**：把 `codeBaseRoot` 完全由用户传。否决：会与 `feedback_search_service_impact_must_pass_codebaseroot.md` 记下的踩坑事实冲突 —— 必须有兜底，且兜底缺失要显式提示。

### 4. 文件命名直接用 `<id>`，不做大小写/分隔符归一化
- **Why**：迁移 plan 工具的下游消费方期望 id 字符串原样出现在文件名中，方便反查；同时人类可读。
- **Alternative considered**：把 id 转成 kebab-case 落盘。否决：会引入 `commandId → kebab` 的命名规则，本变更的范围是 skill，不是命名约定。

### 5. 出错也落盘，且带 `# status:` 行
- **Why**：迁移制定者最怕"以为跑成功但其实失败"。强制落盘 + status 行让结果文件本身成为可审计对象；下游脚本可以 grep `^# status:` 决定是否要 fallback。
- **Alternative considered**：出错时不落盘、只回话。否决：把"成功"和"失败"在文件系统层面就区分开，能避免后续把空 plan 当真用。

### 6. SKILL.md 用 frontmatter 声明依赖 + 入口指引
- **Why**：Claude Code 加载 skill 时 frontmatter 是元信息通道；把 `requires: codegraph-mcp` 写进去，未来若有依赖校验工具可直接读取。
- **Alternative considered**：完全靠正文段落说明。否决：与环境里已有的 skill 习惯（参见 `.claude/skills/openspec-propose/SKILL.md`）不一致。

## Risks / Trade-offs

- **Risk**：`search_service_impact` 返回的是结构化 JSON，列表字段名可能随 MCP 实现版本变化。→ Mitigation：在脚本里用 `data.get("files") or data.get("affected") or data.get("result")` 这种"键名探测"先保守解析；解析全失败时回退到把整个 JSON dump 进 `# reason:` 行而不是丢弃。
- **Risk**：`codeBaseRoot` 在 Windows 下用 `D:/2026/MobileMoneyMonorepo` 写法，脚本里 `os.walk` 与写文件都得统一为正斜杠。→ Mitigation：脚本入口做 `pathlib.Path` 归一化；输出文件的绝对路径以 `Path.resolve().as_posix()` 形式落盘，与示例一致。
- **Risk**：用户对同一 id 重复执行 `<id>-plan.txt` 会被覆盖。→ Mitigation：MVP 阶段直接覆盖（与 `git diff` 工作流一致；不引入历史）；若未来需要"追加 -plan.v2.txt"再单独立项。
- **Risk**：MCP 调用在 Claude Code 会话中具有上下文约束（不能并行触发多个 long-running 工具），但本 skill 单次只调一个 tool，落在安全区。→ Mitigation：不引入并发。

## Migration Plan

无回退成本：本变更仅新增文件（`.claude/skills/propose-migration/SKILL.md`、`scripts/propose_migration.py`），未改动任何现存 capability。若需下线，删除这两个文件即可，不影响 mm-codegraph MCP server、其他 skill 或已落盘的 `<id>-plan.txt`。

## Open Questions

- 是否需要把 `<id>-plan.txt` 的同 id 历次输出合并到一个 `<id>-plan.history/` 目录？目前倾向不做（保持 MVP 简单）。
- 输出格式要不要附带"分析时间 / 调用时长"？目前倾向在第一行 schema 元信息后加 `# generated_at: <iso8601>` —— 成本低、对审计友好，等 design 落地时一起决定。
