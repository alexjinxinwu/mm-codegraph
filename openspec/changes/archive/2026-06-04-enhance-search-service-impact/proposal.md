## Why

当前 `search_service_impact` MCP tool 的 `_traverse_forward` 仅沿 14 张表的外键做 BFS 遍历，能拿到 `service_entry → flow/logic/bean → java_classes` 链上的 `xml_path` / `file_path`。

**测试用例约定：** `ReleaseOrgOperatorCCSuspendStatus.txt` 的 17 行清单**仅**适用于固定入口 `commandId='ReleaseOrgOperatorCCSuspendStatus'`——是该 commandId 下的事实性断言，不是 search_service_impact 的通用契约。其它 commandId 的 files 集合不保证与该 17 行有任何特定关系。

但参考 `AICodeMigrationKit/TxnMigration/FlowAndChainAnalyzer/analyzer.py` 的 `run_entity(command_id)` / `run_flow(flow_id)` 处理链，"按入口找涉及文件"的语义比 ER 遍历多出几类关键来源：

1. **特殊类（Fix-B / Fix-C / Fix-D 启发式）**——ER 关系里没有：
   - `%BuildAuditLog%` 模糊匹配的审计日志类
   - `{identifier}Convertor` 命名匹配的转换器类
   - `extends AbstractIdentityActionNotificationParamCollector` / `AbstractCallBackAGParameterMessageEvent` / `AbstractNotificationResolverAdaptor` 的通知类
   - `extends ReceiverPartyCollector` / `InitiatorParentPartyCollector` 的状态收集器类
   - 父包以 `bridge.` 开头且 `implements *BusinessLogic*` 的同包实现类（bridge_sibling）
2. **REF_CHAIN 递归展开**——`logic_steps.logic_type = 'REF_CHAIN'` 时 `bridges.bridge_id` 引用另一个 chain，需递归展开。
3. **java import 图 BFS**——`analyzer.py` 沿 `java_classes.imports` 字段从 l1 出发做 BFS，并对 interface 节点补实现类。
4. **Fix-E 动态 chain**——通过扫描 `method_bodies` / `source_text` 中的 `setChainId("...")` 字面量发现运行时注入的 chain。
5. **跨表 xml_path 收集**——`flows/states/activities/transitions` + `logics/logic_steps/bridges` + `beans` + `module_parameters` + `service_entries` + `flow_tasks` 的 xml_path 全部纳入。
6. **可选的资源目录扫描（Plan B）**——`search_service_impact` 新增 `codeBaseRoot: str = None` 可选参数。caller 传入时，server 复用 `analyzer.py:scan_resource_files`（line 593-616）的 `os.walk` 逻辑，扫描 `{codeBaseRoot}/resources/{module-parameter, namingsql}/*.xml`，把 3 个资源 XML 纳入 `files`。这与 `migration_gui_tab1.py` 通过 `parse_analysis` 消费 analyzer.py 文本输出的语义等价——GUI 自身不读 XML，由 analyzer.py 代劳；本 server 既然替代 analyzer.py 在该步骤的作用，就自己实现一次等价扫描。

**本 change 不做任何基线（1.0Base / 2.0Base）过滤**——`schema` 是数据源切换器：1.0Base schema 调一次拿到 1.0 文件，2.0Base schema 调一次拿到 2.0 文件，公共库 schema 调一次拿到公共库文件。`files` 集合就是该 schema 命中的全部文件，由调用方按 schema 选择。

**Plan A（实现策略）：** `search_service_impact` 的 `files` 集合**仅**由 `_explore_phase` + `_scan_resource_files` 提供。**显式不调用** `_traverse_forward` / `_traverse_backward`——它们会从 entry flow 出发沿所有 states / activities 扩散，把整个 flow 上的 5000+ 噪音文件（如 `bod_aml` / `bod_bank` 等与本 commandId 业务无关的类）收上来。这与 analyzer.py 的 chain 派生语义不符，也与 `ReleaseOrgOperatorCCSuspendStatus` 的 17 行事实断言不符。`_traverse_forward` / `_traverse_backward` 函数本身**保留**（不删除，不影响其它可能调用方），仅不在 `search_service_impact` 中调用。

**实际场景：** 迁移工具调用方传入 `commandId="ReleaseOrgOperatorCCSuspendStatus"`，期望拿到 17 行 1.0Base 文件清单。当前的 `search_service_impact` 缺特殊类发现等逻辑，结果会少 4 行（audit_log × 2、convertor × 1、party_collector × 1）以及部分 XML（如果该 schema 没把资源目录 XML 的 xml_path 全部收录）。增强后该命令在 1.0Base schema 上能完整输出 17 行；在 2.0Base schema 上同命令则输出 2.0 改造后的对应文件集（同一 commandId 模式，不同 schema 表现不同）。

## What Changes

**增强现有 `search_service_impact`：**
- 不再新增独立 tool
- 在 `search_service_impact` 内部新增处理段（不破坏现有签名）：
  1. **chain 递归展开**：解析 `logic_steps.logic_type = 'REF_CHAIN'` 时 `bridges.bridge_id` 引用另一 chain，递归收集 before_beans FQN + bridge_id
  2. **Fix-B audit_log**：`java_classes.class_name LIKE '%BuildAuditLog%'` + l1 5 级包前缀白名单
  3. **Fix-B convertor**：`java_classes.class_name = ?`（`{commandId}Convertor`）
  4. **Fix-C notification / ag_notification / notification_resolver / party_collector**：extends / implements 抽象类，按 l1 5 级包前缀筛选
  5. **Fix-D bridge_sibling**：l1 中所有 `bridge.` 父包，`package_name LIKE '<parent>.%' AND implements_interfaces LIKE '%BusinessLogic%'`
  6. **java import 图 BFS**：从 `l1_fqns` 出发，沿 `java_classes.imports` 字段展开，对 interface 找实现类
  7. **file_path 收集**：所有 discovered FQN 反查 `java_classes.file_path`；特殊类的 FQN 同样反查
  8. **xml_path 收集**：`flows/states/activities/transitions WHERE flow_id=?` ∪ `logics/logic_steps/bridges WHERE chain_id IN (...)` ∪ `beans WHERE bean_id IN (...)` ∪ `service_entries.xml_path` ∪ `flow_tasks.xml_path`

**入参兼容：**
- 现有 4 个必填/默认参数（`schema / commandId / flowId / direction / maxDepth`）位置与语义 **MUST 不变**
- **新增** `codeBaseRoot: str = None` 放最末位（Plan B），可选；caller 传入时触发资源目录扫描
- **不**新增 baseFilter / isBaseMaster 等过滤参数
- 返回 JSON 结构 `entryPoint / direction / totalImpacted / files / impactChain / warnings` **不变**

**输出文件无基线过滤：**
- `files` 集合就是 `schema` 命中的所有路径（`java_classes.file_path` + 各表 `xml_path`），不再做任何 1.0 / 2.0 / 公共库前缀判断
- 调用方根据传入的 `schema` 自行选择 1.0Base / 2.0Base / 公共库
- 不引入 2.0Base 路径——但这不是因为代码过滤，而是因为 `schema` 已经把数据源切到了 1.0Base 就拿不到 2.0 路径，切到 2.0Base 就拿不到 1.0 路径

**代码：**
- 修改 `codegraph-mcp/codegraph-server.py`
  - 扩展 `search_service_impact` 主流程
  - 新增内部函数：
    - `_expand_chains_recursive(schema, chain_ids)` —— REF_CHAIN 递归展开
    - `_collect_l1_fqns_from_beans(schema, bridge_ids)` —— bridge_id → beans.bean_class
    - `_extends_or_implements_in_pkg5(schema, abstract_cls, l1_pkg5, allow_classname_kw="")` —— 抽象类发现
    - `_discover_special_classes(schema, identifier, l1_fqns)` —— Fix-B/C/D 启发式落地为 SQL
    - `_bfs_import_graph(schema, seeds, l2_excluded)` —— import 图 BFS
    - `_collect_java_files_from_fqns(schema, fqns)` —— file_path
    - `_collect_xml_paths(schema, flow_ids, chain_ids, bean_ids)` —— 跨表 xml_path（含 `module_parameters` 表）
    - `_find_dynamic_chain_ids(schema, fqns)` —— Fix-E 动态 chain 正则扫描
    - `_scan_resource_files(code_base_root, xml_paths)` —— 复用 `analyzer.py:scan_resource_files` 逻辑，`os.walk` 扫描 `resources/{module-parameter, namingsql}/*.xml`

**数据层变更：**
- 复用现有 14 张表；无表结构变更
- 假设 `java_classes.method_bodies` / `source_text` 字段存在（Fix-E 动态 chain 用）；若不存在则该段静默跳过并打 warning

## Capabilities

### New Capabilities
- （无）

### Modified Capabilities
- `codegraph-mcp`：`search_service_impact` 的语义由"纯 ER 遍历"扩展为"ER 遍历 + analyzer.py 启发式"，结果 `files` 列表更接近 analyzer.py 在该 schema 上的实际文件集合。该改动对 1.0Base / 2.0Base / 公共库 schema 都适用，由调用方选择 schema。

## Impact

**代码：**
- 修改 `codegraph-mcp/codegraph-server.py`（`search_service_impact` 内部 + 新增 8 个内部函数）
- 不动 `_traverse_forward` / `_traverse_backward` / `_collect_files` 的现有签名，但会让 `files` 收集来源多出几路

**依赖：**
- 复用现有 schema 14 张表
- 假设 `java_classes.method_bodies` / `source_text` 字段存在（Fix-E）
- 假设 `java_classes.imports` 字段是 FQN 列表（逗号分隔）

**测试：**
- 手工验证 1：调用 `search_service_impact(schema="<1.0Base_schema>", commandId="ReleaseOrgOperatorCCSuspendStatus")`，`files` 集合应包含 `ReleaseOrgOperatorCCSuspendStatus.txt` 17 行（去重后）
- 手工验证 2：调用 `search_service_impact(schema="<2.0Base_schema>", commandId="ReleaseOrgOperatorCCSuspendStatus")`，应返回 2.0 改造后的对应文件集（同一 commandId 模式，不同 schema 数据）
- 边界用例：未命中 commandId、flowId 入口、动态 chain 触发重跑
