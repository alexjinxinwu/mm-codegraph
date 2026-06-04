## 1. 内部辅助函数（9 个）

- [x] 1.1 `_expand_chains_recursive(schema, initial_cids, visited)` —— REF_CHAIN 递归展开，循环 visited 防环
- [x] 1.2 `_collect_l1_fqns_from_beans(schema, bridge_ids)` —— bridge_id 查 beans.bean_class，返回 FQN 集合
- [x] 1.3 `_extends_or_implements_in_pkg5(schema, abstract_cls, l1_pkg5, allow_classname_kw="")` —— 按 extends_class / implements_interfaces 查抽象类的实现，包前缀白名单 + 类名关键词二次过滤
- [x] 1.4 `_discover_special_classes(schema, identifier, l1_fqns)` —— 7 类特殊类（audit_log/convertor/notification/ag_notification/notification_resolver/party_collector/bridge_sibling）
- [x] 1.5 `_bfs_import_graph(schema, seeds, max_nodes=5000)` —— 沿 imports 字段 BFS，interface 补实现类
- [x] 1.6 `_collect_java_files_from_fqns(schema, fqns)` —— FQN 集合反查 java_classes.file_path
- [x] 1.7 `_collect_xml_paths(schema, flow_ids, chain_ids, bean_ids)` —— 跨表收集 xml_path（含 module_parameters 表）
- [x] 1.8 `_find_dynamic_chain_ids(schema, fqns)` —— Fix-E 正则扫 method_bodies / source_text，try/except 兜底
- [x] 1.9 `_scan_resource_files(root, xml_paths)` —— 复用 analyzer.py 的 `scan_resource_files` 逻辑（os.walk 扫描 `resources/{module-parameter, namingsql}/*.xml`），返回额外的 XML 路径列表

## 2. 主流程改造

- [x] 2.1 解析入口：commandId → service_entries / flowId → flows → service_entries.flow_id（沿用现有）
- [x] 2.2 收集 entry 上的 chain_id（逗号分隔）+ flow_id（逗号分隔）
- [x] 2.3 收集 flow_tasks.logic → ft_chains
- [x] 2.4 `_expand_chains_recursive(se_chains ∪ ft_chains)` → all_chain_ids
- [x] 2.5 从 all_chain_ids 收集 bridge_ids（bridges WHERE chain_id IN ...，且非空）
- [x] 2.6 `_collect_l1_fqns_from_beans(bridge_ids)` → l1_fqns
- [x] 2.7 `_discover_special_classes(commandId, l1_fqns)` → special
- [x] 2.8 `_bfs_import_graph(seeds = l1_fqns ∪ special["all"], migrated_schema = <2.0Base schema>)` → all_cls（按 analyzer.py:analyze_classes 等价机制：每个待展开 FQN 查 2.0Base 是否有同名类，已迁移则 `continue` 不展开）
- [x] 2.8.1 `_class_exists_in_other_schema(schema, target_schema, fqn)` —— 取 simple_name 查 target_schema.java_classes；schema 不可达时返回 False（不阻断）
- [x] 2.9 `_find_dynamic_chain_ids(all_cls.keys())` → 新 chain，重跑 2.4-2.8（Fix-E 触发条件：新 chain 非空）
- [x] 2.10 `_collect_java_files_from_fqns(all_cls ∪ special)` → java_files
- [x] 2.11 `_collect_xml_paths(flow_ids, all_chain_ids, bridge_ids)` → xml_files
- [x] 2.12 **新增**：若 caller 传入 `codeBaseRoot`，调用 `_scan_resource_files(codeBaseRoot, xml_files)` → resource_files，与 xml_files 并集
- [x] 2.13 把 java_files / xml_files / resource_files 注入到 `files` dict
- [x] 2.14 **Plan A**：**不**调用 `_traverse_forward` / `_traverse_backward`（避免 5000+ 噪音扩散）
- [x] 2.15 完成后做并集去重 + 升序
- [x] 2.16 返回 JSON 结构保持：`{entryPoint, direction, totalImpacted, files, impactChain, warnings}`（`impactChain` 为空列表）

## 3. 签名扩展（Plan B 新增）

- [x] 3.0 **新增可选参数** `codeBaseRoot: str = None`
  - 当为 None：保持现有行为，依赖 schema 索引收录
  - 当非 None：视为 caller 给出的代码库根目录绝对路径，触发 `_scan_resource_files` 扫描
  - 不破坏现有 4 个必填/默认参数的位置
- [x] 3.0.1 新签名：
  ```python
  def search_service_impact(
      schema: str,
      commandId: str = None,
      flowId: str = None,
      direction: str = "both",
      maxDepth: int = 20,
      codeBaseRoot: str = None,   # 新增
  ) -> str:
  ```
- [x] 3.0.2 `codeBaseRoot` 安全校验：
  - 必须是字符串且非空（None 视作未启用）
  - 必须是绝对路径（os.path.isabs）
  - 必须存在且是目录（os.path.isdir）
  - 校验失败抛 ValueError

## 4. 不破坏的契约

- [x] 4.1 现有 4 个参数（`schema / commandId / flowId / direction / maxDepth`）位置与参数校验逻辑不变（**`direction` / `maxDepth` 当前实现不使用，但参数仍接收并校验**）
- [x] 4.2 入口解析逻辑（`commandId → service_entries` / `flowId → flows → service_entries.flow_id`）保持不变
- [x] 4.3 `impactChain` 输出结构不变（当前为空列表，保留字段语义以备未来扩展）
- [x] 4.4 `warnings` 列表不变；新增 warning 类型：
  - `"Dynamic chain scan skipped: <reason>"`
  - `"Import BFS truncated at max_nodes=5000"`
  - `"Resource directory scan skipped: codeBaseRoot not provided"`
  - `"Resource directory scan failed at <path>: <error>"`（os.walk 抛错时）
- [x] 4.5 **不**对 `files` 做任何基线过滤（1.0Base / 2.0Base / 公共库前缀均不过滤）
- [x] 4.6 `_scan_resource_files` 的行为与 `analyzer.py:scan_resource_files`（line 593-616）等价：
  - 同样的 `_TARGET_DIRS = {"module-parameter", "namingsql"}`
  - 同样的"对每个 xml_path 找 `\\resources\\` 之前的根"逻辑
  - 同样的 `os.walk(root/resources/)` + dirname 白名单扫描
  - 同样的 `os.path.relpath` 相对化

## 5. 手工验证

⚠️  **`ReleaseOrgOperatorCCSuspendStatus.txt` 的 17 行只适用于固定入口
`commandId='ReleaseOrgOperatorCCSuspendStatus'`** —— 这是该 commandId 下的
**事实性断言**，不是 search_service_impact 的通用契约。其它 commandId 的
files 集合不保证与该 17 行有特定关系。

- [ ] 5.1 准备 MySQL 实例并导入 1.0Base schema 数据
- [ ] 5.2 不传 `codeBaseRoot` 调用：`search_service_impact(schema="<1.0Base>", commandId="ReleaseOrgOperatorCCSuspendStatus")`
- [ ] 5.3 传 `codeBaseRoot` 调用：`search_service_impact(schema="<1.0Base>", commandId="ReleaseOrgOperatorCCSuspendStatus", codeBaseRoot="D:/path/to/1.0BaseMaster")`
- [ ] 5.4 把 5.3 的 `files` 列表排序后写入临时文件，与 `ReleaseOrgOperatorCCSuspendStatus.txt`（17 行）做 diff，要求 0 行差异
- [ ] 5.5 比对 5.2 与 5.3 的 `files` 集合大小——5.3 应当 ≥ 5.2，差距来自 3 个 module-parameter/namingsql XML
- [ ] 5.6 边界用例：commandId 不存在应返回 `totalImpacted: 0` + warning
- [ ] 5.7 边界用例：flowId 入口应得到相同 17 行（前提是 flowId 与 commandId 指向同一流程）
- [ ] 5.8 边界用例：commandId 触发了动态 chain（如果有）应自动扩展
- [ ] 5.9 边界用例：超大 import 图（> 5000 节点）应截断并产生 warning
- [ ] 5.10 边界用例：`codeBaseRoot` 传非法路径（不存在 / 不是目录 / 不是绝对路径）应抛 ValueError
- [ ] 5.11 边界用例：`codeBaseRoot` 传一个有效目录但里面没有 `resources/{module-parameter,namingsql}` 子目录，应正常返回不报错
- [ ] 5.12 **跨 schema 验证**：调用 `search_service_impact(schema="<2.0Base>", commandId="ReleaseOrgOperatorCCSuspendStatus", codeBaseRoot="<2.0Root>")`，应返回 2.0 改造后的对应文件集
- [ ] 5.13 **公共库验证**：调用 `search_service_impact(schema="<公共库>", commandId="<公共库命令>", codeBaseRoot="<公共库根>")`，应返回公共库文件集
