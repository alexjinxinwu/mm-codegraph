## Context

当前 mm-codegraph 系统缺少一种快速定位"修改某个服务入口会影响哪些文件"的能力。团队在进行代码变更时，无法直观了解影响范围。

**现状：**
- `service_entries` 表记录了所有服务入口（含 command_id、flow_id、chain_id）
- ER 关系跨越 13 张表：flows（状态机）、logics（逻辑链）、bridges（桥接器）、beans（Java类）、activities、transitions、states、flow_tasks、logic_steps、interceptors、java_classes、java_methods
- 手工追踪需要跨多张表查询，效率低且易遗漏

**约束：**
- Python 3 + MySQL（pymysql + dbutils）
- MCP Server 实现：`codegraph-mcp/codegraph-server.py`
- 通过 MCP `@mcp.tool()` 暴露给 Claude Code

**干系人：**
- 开发人员：变更前评估影响范围
- 测试人员：确定测试用例覆盖边界
- 运维/安全审查：评估变更风险

---

## Goals / Non-Goals

**Goals:**
- 提供新的 MCP tool `search_service_impact`，通过 `commandId` 或 `flowId` 查询影响范围
- 基于 13 张表的 ER 关系网络遍历
- 同时支持正向（触发下游）和反向（被上游触发）两个方向
- 输出受影响文件的去重列表（含 Java 源文件 + XML 配置文件）

**Non-Goals:**
- 不做跨语言/跨服务的 RPC 追踪（当前仅限本系统 ER 关系）
- 不做实时代码依赖分析（如 import 语句分析）
- 不提供修改建议或自动影响评估分数
- 不做增量索引或变更监控

---

## Decisions

### Decision 1: BFS 遍历策略

使用 Breadth-First Search 遍历 ER 图，而非递归 CTE 或预计算索引。

**13 张表的 ER 遍历路径：**

**正向遍历 (Forward)：**
```
service_entry
  ├──[chain_id]──→ logics
  │                 ├──[chain_id]──→ logic_steps
  │                 └──[chain_id]──→ bridges
  │                                ├── before_beans (FQN) ──→ beans.bean_class
  │                                └── after_beans  (FQN) ──→ beans.bean_class
  │                                                          └── java_classes.java_path
  │
  ├──[flow_id]──→ flows
  │                 └──[flow_id]──→ states
  │                               ├── activities.logic ──→ logics.chain_id (递归)
  │                               └── transitions
  │                                     ├── activity_id ──→ activities.activity_id
  │                                     ├── next_target ──→ states.state_name (递归)
  │                                     └── state_name ──→ states (递归)
  │
  ├──[bean_ref]──→ beans.bean_id ──→ java_classes.java_path
  │
  └──[context_name]──→ interceptors.context_name
                         └── bean_ref ──→ beans.bean_id ──→ java_classes.java_path
```

**反向遍历 (Backward)：**
```
service_entry (target)
  ├─ 哪些 service_entry.flow_id = flows.flow_id 指向当前
  ├─ 哪些 service_entry.chain_id = logics.chain_id 指向当前
  ├─ 哪些 activities.logic = logics.chain_id 指向当前
  ├─ 哪些 flow_tasks.logic = logics.chain_id 指向当前
  ├─ 哪些 transitions.next_target = states.state_name 指向当前 state
  └─ 哪些 bridges.before_beans / after_beans = beans.bean_class 指向当前 bean
```

**选择理由：**
- Python 实现简单直接，便于调试和维护
- 无数据库递归深度限制
- 可灵活控制遍历方向和深度

**备选对比：**
| 方案 | 优点 | 缺点 |
|------|------|------|
| 递归 CTE | 数据库层完成 | MySQL 深度限制、调试困难 |
| 预计算索引 | 查询快 | 维护成本高、更新延迟 |
| BFS 应用层遍历 | 可读性强、无限制 | 应用层开销稍高 |

### Decision 2: 双向搜索

`direction` 参数支持 `forward`、`backward`、`both`。

**实现：**
- **Forward**: 从 service_entry 出发，沿 `flow_id` 和 `chain_id` 向下游遍历
- **Backward**: 反向追踪，查找哪些 service_entry / activities / flow_tasks / transitions 的引用指向当前入口
- **Both**: 同时返回两个方向的结果

### Decision 3: 文件去重策略

使用 Python `set` 基于 `file_path` 去重，确保同一文件仅出现一次。

**纳入输出的文件类型：**
- Java 源文件（`java_classes.file_path`）
- XML 配置（各实体的 `xml_path`）

### Decision 4: 深度限制

`maxDepth=20` 作为默认最大深度，防止因环形依赖导致无限递归。

**环路处理：**
- 用 `visited` set 记录已访问节点
- 检测到环路时跳过，避免死循环

---

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| **大图遍历耗时** | 深层调用链或大量下游节点可能导致响应慢 | `maxDepth` 限制 |
| **循环依赖截断** | A→B→C→A 环形依赖，可能漏掉有效路径 | visited 机制、返回环路警告 |
| **N+1 查询问题** | 每个节点多次查询数据库 | 批量 in 查询优化 |

---

## Migration Plan

**Phase 1: 新增 MCP tool**
1. 在 `codegraph-mcp/codegraph-server.py` 新增 `search_service_impact` 函数
2. 内部实现 BFS 遍历逻辑
3. 实现单向（forward）遍历

**Phase 2: 功能完善**
4. 添加 backward 遍历
5. 添加环形依赖检测和警告

**Phase 3: 优化与文档**
6. 补充 docstring 和示例
7. 性能优化（批量查询）

**回滚策略：**
- 删除 `search_service_impact` 函数即可
- 不影响其他 MCP tools

---

## Open Questions

1. ~~Backward 遍历的完整路径如何定义？~~ （已解答：见 Decision 1 的反向遍历路径）
2. **性能基准：** 单次查询最大响应时间期望是多少（100ms / 500ms / 1s）？
3. **是否需要缓存？** 高频查询场景可能需要
