# Service Impact Search API Implementation Plan

> **For agentic workers:** Use `opsx:apply` to implement this plan task-by-task via subagent-driven-development.

**Goal:** 在 mm-codegraph MCP Server 新增 `search_service_impact` tool，支持通过 commandId 或 flowId 查询服务在 13 表 ER 关系网络中的影响传递，输出受影响文件列表。

**Architecture:**
- Python 3 + MySQL (pymysql + dbutils)
- MCP Server：`codegraph-mcp/codegraph-server.py`
- 新增 `@mcp.tool()` 函数 `search_service_impact`
- BFS 图遍历实现 ER 关系追踪

**Tech Stack:** Python 3, MySQL, MCP (FastMCP)

**ER 遍历路径（正向 Forward）：**
```
service_entry
  ├─[chain_id]──→ logics ─[chain_id]──→ logic_steps + bridges
  │                                     ├─[before_beans]──→ beans.bean_class
  │                                     └─[after_beans]──→ beans.bean_class
  ├─[flow_id]──→ flows ─[flow_id]──→ states
  │                            ├─ activities.logic ───→ logics.chain_id
  │                            └─ transitions.next_target ───→ states.state_name
  ├─[bean_ref]──→ beans.bean_id ──→ java_classes.java_path
  └─[context_name]──→ interceptors.context_name ──→ bean_ref ──→ beans
```

---

## Task 1: MCP Tool 框架

- [ ] **Step 1.1:** 在 `codegraph-mcp/codegraph-server.py` 新增 `search_service_impact` 函数
- [ ] **Step 1.2:** 添加 `@mcp.tool()` 装饰器
- [ ] **Step 1.3:** 定义参数：`schema`, `commandId` (可选), `flowId` (可选), `direction` (default="both"), `maxDepth` (default=20)
- [ ] **Step 1.4:** 实现参数校验 — 至少提供 commandId 或 flowId
- [ ] **Commit:** `git add . && git commit -m "feat: add search_service_impact MCP tool skeleton`

---

## Task 2: BFS 遍历引擎

- [ ] **Step 2.1:** 实现 `traverse_forward(node, visited, depth, max_depth, files, edges)` — 正向 BFS 遍历
- [ ] **Step 2.2:** 实现 `traverse_backward(node, visited, depth, max_depth, files, edges)` — 反向 BFS 遍历
- [ ] **Step 2.3:** 实现 `detect_circular(node_id, visited)` — 环路检测
- [ ] **Step 2.4:** 实现 `collect_files_from_bean(fqn, files)` — 收集 java_path
- [ ] **Step 2.5:** 实现 `collect_xml_path(xml_path, files)` — 收集 xml_path
- [ ] **Step 2.6:** 实现 `deduplicate_files(files)` — 按 file_path 去重
- [ ] **Step 2.7:** 实现 `build_impact_chain(edges)` — 构建 impactChain
- [ ] **Commit:** `git add . && git commit -m "feat: implement BFS traversal engine for service impact search"`

---

## Task 3: 13 表查询函数

- [ ] **Step 3.1:** 实现 `find_service_entry_by_command_id(schema, command_id)`
- [ ] **Step 3.2:** 实现 `find_service_entries_by_flow_id(schema, flow_id)`
- [ ] **Step 3.3:** 实现 `find_service_entries_by_chain_id(schema, chain_id)` — 反向
- [ ] **Step 3.4:** 实现 `find_flow_by_id(schema, flow_id)`
- [ ] **Step 3.5:** 实现 `find_states_by_flow_id(schema, flow_id)`
- [ ] **Step 3.6:** 实现 `find_activities_by_state(schema, state_name, flow_id)`
- [ ] **Step 3.7:** 实现 `find_activities_by_logic(schema, chain_id)` — 反向
- [ ] **Step 3.8:** 实现 `find_transitions_by_state(schema, state_name, flow_id)`
- [ ] **Step 3.9:** 实现 `find_transitions_by_next_target(schema, state_name, flow_id)` — 反向
- [ ] **Step 3.10:** 实现 `find_flow_tasks_by_flow_id(schema, flow_id)`
- [ ] **Step 3.11:** 实现 `find_flow_tasks_by_logic(schema, chain_id)` — 反向
- [ ] **Step 3.12:** 实现 `find_logic_by_chain_id(schema, chain_id)`
- [ ] **Step 3.13:** 实现 `find_logic_steps_by_chain_id(schema, chain_id)`
- [ ] **Step 3.14:** 实现 `find_bridges_by_chain_id(schema, chain_id)`
- [ ] **Step 3.15:** 实现 `find_bridges_by_bean_class(schema, fqns)` — 反向
- [ ] **Step 3.16:** 实现 `find_beans_by_bean_class(schema, fqns)`
- [ ] **Step 3.17:** 实现 `find_beans_by_bean_id(schema, bean_id)`
- [ ] **Step 3.18:** 实现 `find_interceptors_by_context(schema, context_name)`
- [ ] **Step 3.19:** 实现 `find_java_classes_by_paths(schema, paths)`
- [ ] **Commit:** `git add . && git commit -m "feat: add 13-table query functions for service impact search"`

---

## Task 4: 结果组装与响应

- [ ] **Step 4.1:** 实现主入口 `search_service_impact` — 组装正向/反向结果
- [ ] **Step 4.2:** 实现 `out()` 格式化 JSON 输出
- [ ] **Step 4.3:** 添加 docstring 和示例
- [ ] **Commit:** `git add . && git commit -m "feat: complete search_service_impact implementation"`

---

## Task 5: 测试

- [ ] **Step 5.1:** 测试 `traverse_forward` — 验证正向遍历路径
- [ ] **Step 5.2:** 测试 `traverse_backward` — 验证反向遍历路径
- [ ] **Step 5.3:** 测试 `detect_circular` — 验证环形依赖截断
- [ ] **Step 5.4:** 测试 `deduplicate_files` — 验证文件去重
- [ ] **Step 5.5:** 端到端测试 `search_service_impact` — 调用 MCP tool
- [ ] **Commit:** `git add . && git commit -m "test: add tests for search_service_impact"`
