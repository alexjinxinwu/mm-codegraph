---
name: propose-migration
description: 输入一个 commandId 或 flowId，调用 mm-codegraph MCP 的 search_service_impact，默认 schema=1_0_baseline，在 codeBaseRoot 根目录生成 <id>-plan.txt 受影响文件清单。Use when the user wants to draft a migration plan for a service entry / flow and needs the concrete set of source files the change will touch.
license: MIT
compatibility: Requires mm-codegraph MCP server (codekg) registered in Claude Code MCP config.
metadata:
  author: mm-codegraph
  version: "1.0"
  requires:
    mcp: mm-codegraph
  generatedBy: opsx
---

# propose-migration

把"输入一个 id，输出受影响文件清单"做成一条 slash 命令，端到端走通：参数解析 → MCP 调用 → 字典序去重 → 落盘。

## 已验证样例

- 命令：`/propose-migration ReleaseOrgOperatorCCSuspendStatus`
- 输出：`D:/2026/MobileMoneyMonorepo/ReleaseOrgOperatorCCSuspendStatus-plan.txt`
- schema：`1_0_baseline`（默认）
- codeBaseRoot：取自环境变量 `MM_CODEGRAPH_CODEBASE_ROOT`（= `D:/2026/MobileMoneyMonorepo`）
- 落地内容：纯文件列表，17 行受影响源文件相对路径（按 MCP 返回顺序即字典序），**无任何元信息头**

## 触发语法

```
/propose-migration <commandId|flowId> [--schema=<name>] [--codebase=<path>]
```

- `<commandId|flowId>` 必填，单个字符串。
- `--schema=<name>` 可选，默认 `1_0_baseline`。
- `--codebase=<path>` 可选，优先级高于环境变量。

## 依赖检查

在执行本 skill 的任何步骤前，**确认** `mcp__mm-codegraph__search_service_impact` 工具可用：

- 工具存在 → 继续。
- 工具不存在 → **停止**，向用户输出以下指引并退出，不进入执行序列：

  > mm-codegraph MCP server 未注册。请在 Claude Code 的 MCP 配置（如 `~/.claude/.mcp.json` 或等价位置）添加：
  >
  > ```json
  > {
  >   "mcpServers": {
  >     "codekg": {
  >       "command": "python",
  >       "args": ["D:/2026/mm-codegraph/codegraph-mcp/codegraph-server.py"],
  >       "env": {
  >         "MMCG_MYSQL_HOST": "...",
  >         "MMCG_MYSQL_PORT": "3306",
  >         "MMCG_MYSQL_USER": "...",
  >         "MMCG_MYSQL_PASSWORD": "...",
  >         "MM_CODEGRAPH_CODEBASE_ROOT": "D:/2026/MobileMoneyMonorepo"
  >       }
  >     }
  >   }
  > }
  > ```
  >
  > 配置后重启 Claude Code 后再试。

## 执行序列

**必须**严格按以下顺序执行。每一步的失败处理已就位，不得跳过。

### 1. 解析参数

- `<id>` = 用户传入的非前缀参数
- `schema` = `--schema=` 前缀（缺省 `1_0_baseline`）
- `codeBaseRoot` = `--codebase=` 前缀（缺省读 `MM_CODEGRAPH_CODEBASE_ROOT` 环境变量）
- 三者皆无 `codeBaseRoot` → **继续执行但**在响应中明确提示：

  > ⚠️ 未配置 codeBaseRoot，将跳过 resources/namingsql 等资源类扫描。设置环境变量 `MM_CODEGRAPH_CODEBASE_ROOT=<path>` 或在命令中加 `--codebase=<path>` 以获得完整结果。

  然后继续走步骤 2～6（不阻断）。`search_service_impact` 自身会在 `codeBaseRoot` 为空时输出 warning `Resource directory scan skipped: codeBaseRoot not provided`，本 skill 透传该 warning 到 `<id>-plan.txt` 的 `# reason:` 行。

### 2. commandId 优先判定

- 用 `mcp__mm-codegraph__find_service_entry(schema, keyword=<id>, limit=5)` 探测是否存在同名 commandId。
- 用 `mcp__mm-codegraph__search(schema, keyword=<id>, limit=5)` 探测是否存在同名 flowId。
- 若两者都命中 → **以 commandId 为准**，并在响应中打印 `note: matched commandId over flowId`。
- 若仅 commandId 命中 → 调用走 `commandId=<id>`。
- 若仅 flowId 命中（或都不命中）→ 调用走 `flowId=<id>`。

### 3. 调用 search_service_impact

```
mcp__mm-codegraph__search_service_impact(
  schema=<schema>,
  commandId=<id_or_none>,
  flowId=<id_or_none>,
  codeBaseRoot=<codeBaseRoot_or_null>
)
```

返回 JSON 形如：

```json
{
  "entryPoint": "...",
  "direction": "both",
  "totalImpacted": <int>,
  "files": ["<abs path 1>", "<abs path 2>", ...],
  "impactChain": [],
  "warnings": ["..."]
}
```

### 4. 解析受影响文件列表

- 取 `files` 字段；若 `files` 缺省/为 null，按以下键名顺序回退探测：`files` → `affected` → `result`。
- 全部为 null → 视为空集（status=empty）。
- 解析得到 `Set[str]` 文件路径集合。
- 字典序升序排序：`sorted(paths)`。
- 去重：集合天然去重。
- 过滤：去除空字符串与非字符串元素。

### 5. 写文件 `<id>-plan.txt`

文件路径：**`{codeBaseRoot}/<id>-plan.txt>`**（`codeBaseRoot` 缺失时改用当前 shell 工作目录探测值，仍缺失则报错不写盘）。

文件内容（UTF-8，行尾 `\n`）：**只包含纯粹的文件列表**，每行一条受影响的源文件路径，**不写任何元信息头**（无 `# schema:` / `# status:` / `# reason:` 行）。

- MCP 返回的 `files` 元素是**相对 `codeBaseRoot` 的反斜杠分隔路径**（如 `1.0BaseMaster\BD_BOD\codes\…\Foo.java`）。本 skill **原样落盘**，不强行转为绝对路径。
- 字典序：MCP 返回顺序即字典序，按 MCP 原序写入即可；如需强制重排可 `sorted(paths)`。
- 空集：写一个空文件（0 字节），**不**写占位文字。
- 异常：MCP 抛错 → **不写盘**，在响应中报错并贴出 reason。

用 `Write` 工具写出（`codeBaseRoot` 不存在 → **不写盘**，在响应中报错并贴出 reason）。

### 6. 回报

在响应中**必须**包含以下 4 项（仅在响应里贴，**不写进文件**）：

- `Wrote: <absolute path to <id>-plan.txt>`（让用户能 grep 确认落盘）
- `Entry point: <commandId|flowId>`
- `File count: <N>`（0 表示空文件）
- `Warnings: <list>`（MCP 返回的 warnings 数组；无 warning 时为 `none`）

## 边界与失败处理

| 场景 | 行为 |
|------|------|
| `<id>` 与 `commandId` / `flowId` 都未命中 | 仍写 `<id>-plan.txt`（0 字节空文件），不写占位文字 |
| `codeBaseRoot` 缺失 | 不阻断；MCP 返回 warning；本 skill 在响应中提示 |
| `codeBaseRoot` 路径不存在 | **不写盘**；响应中报错并把 reason 贴出 |
| MCP 工具抛异常 | **不写盘**；响应中报错并把异常前 200 字贴出 |
| 重复执行覆盖 | 直接覆盖（与 `git diff` 工作流一致；不引入历史） |

## 命名约束

- `<id>-plan.txt` 中 `<id>` **保持用户原始大小写与分隔符**（如 `ReleaseOrgOperatorCCSuspendStatus` 不改成 kebab-case）。
- 文件名禁止含 `/`、`\`、`:`、`*`、`?`、`"`、`<`、`>`、`|`；若 `<id>` 命中其中任一字符，把字符替换为 `_` 再写盘并在响应中提示已替换。

## 不做什么

- 不重写 `search_service_impact` 的遍历算法。
- 不做结果可视化（不写 JSON、不画图、不生成 dot 图）。
- 不支持批量输入（一次一个 id；批量留给将来的 batch-skill）。
- 不与 Git 集成（不自动 commit、PR）；落盘后由用户/后续工具接手。
