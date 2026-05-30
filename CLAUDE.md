# Claude Code — opensuperdemo

本仓库是 **OpenSpec + Superpowers（Superspec）** 的 Harness 演示项目。

## 开始前

1. 阅读 `openspec/project.md` 与 `openspec/config.yaml` 中的 context
2. 规格真源：`openspec/specs/`
3. 安装 Superpowers（Claude Code 插件市场）：
   ```
   /plugin marketplace add obra/superpowers-marketplace
   /plugin install superpowers@superpowers-marketplace
   ```
4. 若缺少 `/opsx:*` 命令，在项目根执行：`bash scripts/setup-openspec.sh`

## 工作流（Superspec）

| 阶段 | 命令 |
|------|------|
| 新变更 | `/opsx:new <kebab-name>` |
| 继续产物 | `/opsx:continue` |
| 快进产物 | `/opsx:ff <name>` |
| 实现（TDD + 子代理） | `/opsx:apply` |
| 验证 | `/opsx:verify` |
| 归档 | `/opsx:archive` |

实现阶段会按 schema 调用 Superpowers：`using-git-worktrees`、`subagent-driven-development`、`test-driven-development` 等。

## 实现约定

- 保持 controller → service → repository 分层，不在 controller 写业务逻辑
- 新 REST 接口放在 `/api/v1` 下
- 先写/更新 OpenSpec 需求与场景（含 SHALL/MUST 与 `#### Scenario:`），再写代码
- 本地：`docker compose up -d` 后 `mvn spring-boot:run`
