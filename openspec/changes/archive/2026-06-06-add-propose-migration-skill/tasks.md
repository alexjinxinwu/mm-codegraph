## 1. skill 入口与依赖声明

- [ ] 1.1 在 `.claude/skills/propose-migration/SKILL.md` 写 frontmatter（name + description + requires: codegraph-mcp），正文给出触发语法 `/propose-migration <commandId|flowId>` 与可识别的前缀选项 `--schema=<name>`、`--codebase=<path>`
- [ ] 1.2 SKILL.md 正文固定 LLM 执行序列：① 解析参数 → ② 校验 `codeBaseRoot`（缺则提示）→ ③ 调 `mcp__mm-codegraph__search_service_impact` → ④ 解析 `files[]` → ⑤ 字典序去重 → ⑥ 写 `<id>-plan.txt`（含 schema / status / reason 三行元信息头）
- [ ] 1.3 SKILL.md 末尾给出 MCP 未注册时的引导段落（指向 `codegraph-mcp/codegraph-server.py` 与 Claude Code MCP 配置示例）并写明退出策略

## 2. 文件输出契约固化到 SKILL.md

- [ ] 2.1 在 SKILL.md 中明确"commandId 优先于 flowId"，且在 stdout 打印 `note: matched commandId over flowId`
- [ ] 2.2 在 SKILL.md 中明确首行格式 `# schema: <schema>`，第二行 `# status: <ok|empty|error>`，第三行 `# reason: <text>`，其后为字典序绝对路径列表（`Path.resolve().as_posix()` 形式）
- [ ] 2.3 在 SKILL.md 中明确"出错的 MCP 返回 / 空集 / codeBaseRoot 缺失 / codeBaseRoot 不存在目录"四种状态分支的处理

## 3. 集成与测试

- [ ] 3.1 在 Claude Code 会话中以 `/propose-migration ReleaseOrgOperatorCCSuspendStatus` 触发，确认产出 `D:/2026/MobileMoneyMonorepo/ReleaseOrgOperatorCCSuspendStatus-plan.txt`，首行 `# schema: 1_0_baseline`，正文按字典序列出受影响的源文件绝对路径
- [ ] 3.2 用一个不存在的 id（例如 `NonexistentCommandForTest`）跑一次，确认文件首行为 `# status: empty` 且 `reason: no affected files found`
- [ ] 3.3 临时把 `codeBaseRoot` 指向不存在的路径（例如 `--codebase=D:/no/such/dir`），确认给出明确错误并不写盘（或写盘时 `# status: error` 含 reason）
- [ ] 3.4 SKILL.md 顶部加一段"已验证样例"，指向 step 3.1 产出的文件路径

## 4. 文档与归档准备

- [ ] 4.1 在 `openspec/specs/propose-migration-skill/spec.md` 复核与最终实现一致（不需要改动）
- [ ] 4.2 更新 `openspec/project.md` "已实现能力"表，新增一行 `propose-migration-skill`，spec 指向 `openspec/specs/propose-migration-skill/spec.md`
- [ ] 4.3 把本 change 目录 `git add` 后单独立一个 commit（`docs(openspec): scaffold add-propose-migration-skill change`），作为后续 `/opsx:archive` 前置条件
