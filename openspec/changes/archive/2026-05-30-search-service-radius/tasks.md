## 1. MCP Tool 定义

- [x] 1.1 在 `codegraph-mcp/codegraph-server.py` 新增 `search_service_impact` 函数 — `@mcp.tool()` 装饰器
- [x] 1.2 定义参数：`schema`, `commandId` (可选), `flowId` (可选), `direction` (default="both"), `maxDepth` (default=20)
- [x] 1.3 实现返回值：JSON 格式含 `entryPoint`, `direction`, `totalImpacted`, `files`, `impactChain`, `warnings`

## 2. Repository 层（13 表查询）

- [x] 2.1 复用现有 `q()` 函数执行查询
- [x] 2.2 实现 `find_service_entry_by_command_id` — 通过 `q()` 内联实现
- [x] 2.3 实现 `find_service_entries_by_flow_id` — 通过 `q()` 内联实现
- [x] 2.4 实现 `find_service_entries_by_chain_id` — 反向查找通过 `q()` 内联实现
- [x] 2.5 实现 `find_flow_by_id` — 通过 `q()` 内联实现
- [x] 2.6 实现 `find_states_by_flow_id` — 通过 `q()` 内联实现
- [x] 2.7 实现 `find_activities_by_state` — 通过 `q()` 内联实现
- [x] 2.8 实现 `find_activities_by_logic` — 反向查找通过 `q()` 内联实现
- [x] 2.9 实现 `find_transitions_by_state` — 通过 `q()` 内联实现
- [x] 2.10 实现 `find_transitions_by_next_target` — 反向查找通过 `q()` 内联实现
- [x] 2.11 实现 `find_flow_tasks_by_flow_id` — 通过 `q()` 内联实现
- [x] 2.12 实现 `find_flow_tasks_by_logic` — 反向查找通过 `q()` 内联实现
- [x] 2.13 实现 `find_logic_by_chain_id` — 通过 `q()` 内联实现
- [x] 2.14 实现 `find_logic_steps_by_chain_id` — 通过 `q()` 内联实现
- [x] 2.15 实现 `find_bridges_by_chain_id` — 通过 `q()` 内联实现
- [x] 2.16 实现 `find_bridges_by_bean_class` — 反向查找通过 `q()` 内联实现
- [x] 2.17 实现 `find_beans_by_bean_class` — 通过 `q()` 内联实现
- [x] 2.18 实现 `find_beans_by_bean_id` — 通过 `q()` 内联实现
- [x] 2.19 实现 `find_interceptors_by_context` — 通过 `q()` 内联实现
- [x] 2.20 实现 `find_java_classes_by_paths` — 通过 `q()` 内联实现

## 3. BFS 遍历逻辑

- [x] 3.1 实现 `traverse_forward` — 正向 BFS 遍历
- [x] 3.2 实现 `traverse_backward` — 反向 BFS 遍历
- [x] 3.3 实现 `collect_files` — 收集 bean 的 java_path 和 xml_path
- [x] 3.4 实现 `collect_xml_path` — 收集 xml_path（合并到 _collect_files）
- [x] 3.5 实现 `detect_circular` — 环路检测（通过 visited set）
- [x] 3.6 实现 `deduplicate_files` — 按 file_path 去重（files 是 dict 自动去重）
- [x] 3.7 实现 `build_impact_chain` — 构建 impactChain 列表（通过 _add_edge）

## 4. 参数校验

- [x] 4.1 校验至少提供 commandId 或 flowId
- [x] 4.2 校验 direction 必须为 forward/backward/both
- [x] 4.3 校验 maxDepth 为正整数

## 5. 测试

- [ ] 5.1 测试 `traverse_forward` — 验证正向遍历路径和文件收集
- [ ] 5.2 测试 `traverse_backward` — 验证反向遍历路径
- [ ] 5.3 测试 `detect_circular` — 构造环形依赖，验证不无限递归
- [ ] 5.4 测试 `deduplicate_files` — 验证同一文件只出现一次
- [ ] 5.5 端到端测试 `search_service_impact` — 调用 MCP tool 验证返回结果
