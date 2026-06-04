# Codegraph MCP

## Purpose

通过 MCP 协议向 Claude Code 暴露 MySQL 代码知识图谱的只读查询能力。每个 MySQL database schema 对应一个已索引的代码库，数据模型为 14 表 ER 关系（见 `codegraph-mcp/ER.md`）。MCP Server 实现位于 `codegraph-mcp/codegraph-server.py`。

## Requirements

### Requirement: MCP Server 注册与传输
（沿用原 spec，不变）

### Requirement: Schema 导航
（沿用原 spec，不变）

### Requirement: 服务入口与流程状态机查询
（沿用原 spec，不变）

### Requirement: 逻辑链解析
（沿用原 spec，不变）

### Requirement: Bean 与 Java 类型查询
（沿用原 spec，不变）

### Requirement: 只读 SQL 兜底与安全约束
（沿用原 spec，不变）

### Requirement: 数据库连接配置
（沿用原 spec，不变）

### Requirement: 代码知识图谱 ER 模型
（沿用原 spec，不变）

---

## ADDED Requirements

### Requirement: 服务影响范围（启发式增强）

系统 SHALL 在 `search_service_impact` 中复用 analyzer.py 的 `run_entity` / `run_flow` 处理链（Fix-B/C/D 启发式 + REF_CHAIN 递归展开 + import 图 BFS + 动态 chain 发现 + 可选的资源目录扫描），使 `files` 集合与 analyzer.py 在同一 schema 上的实际文件集合**等价**。该增强对所有 schema（1.0Base / 2.0Base / 公共库）都适用，**由 `schema` 参数决定数据源**——本 change 不做基线过滤。

**Plan A：** `search_service_impact` 的 `files` 集合**仅**由 `_explore_phase` + `_scan_resource_files` 提供。**显式不调用** `_traverse_forward` / `_traverse_backward`——它们会从 entry flow 出发沿所有 states / activities 扩散，把整个 flow 上的 5000+ 噪音文件（与本 commandId 业务无关的类，如 `bod_aml` / `bod_bank` 等）收上来，与 analyzer.py 的 chain 派生语义不符。

#### Scenario: 入口返回完整文件集
- **WHEN** 调用 `search_service_impact(schema="<S>", commandId="ReleaseOrgOperatorCCSuspendStatus")` 且 `service_entries` 表中存在匹配 `command_id` 的记录
- **THEN** 系统 SHALL：
  - 收集 entry 上的 `chain_id`（逗号分隔）与 `flow_id`（逗号分隔）
  - 收集 `flow_tasks.logic` 字段得到 `ft_chains`
  - 调用 `_expand_chains_recursive` 展开 `REF_CHAIN` 递归
  - 从展开后的 chain 集合收集 `bridge_id`，反查 `beans.bean_class` 得到 L1 FQN
  - 调用 `_discover_special_classes(identifier, l1_fqns)` 收集 audit_log / convertor / notification / ag_notification / notification_resolver / party_collector / bridge_sibling
  - 调用 `_bfs_import_graph(seeds=L1 + 特殊类, migrated_schema=<2.0Base schema>)` 沿 `java_classes.imports` 字段 BFS，对每个待展开 FQN 查 2.0Base schema 是否有同名类：若已迁移则 `continue` 不展开（与 analyzer.py:analyze_classes 第 491-497 行等价）
  - 调用 `_find_dynamic_chain_ids` 扫描 `method_bodies` / `source_text` 中的 `setChainId("...")` 字面量；若有新 chain，重跑 chain 展开与 BFS
  - 把所有 discovered FQN 反查 `java_classes.file_path`
  - 调用 `_collect_xml_paths` 跨 `flows/states/activities/transitions/logics/logic_steps/bridges/beans` 表收集 `xml_path`
- **THEN** 系统 MUST NOT 调用 `_traverse_forward` 或 `_traverse_backward`（避免 5000+ 噪音扩散）
- **THEN** 对每个待展开的 FQN，系统 SHALL 通过 `_class_exists_in_other_schema(schema, migrated_schema, fqn)` 检查 2.0Base schema 是否已有同名简单类名：若已迁移，MUST NOT 展开其 imports（与 analyzer.py:analyze_classes 等价）
- **WHEN** `migrated_schema` 不可达（数据库探针失败）或不提供
- **THEN** 系统 SHALL 跳过迁移检查，BFS 按旧版逻辑展开（仍受包前缀与 max_nodes 约束）
- **THEN** 返回 JSON 的 `files` 列表为上述来源的并集去重 + 升序

#### Scenario: 特殊类发现
- **WHEN** L1 FQN 集合非空
- **THEN** 系统 SHALL 至少识别以下 7 类特殊类，全部通过 SQL 而非代码启发式实现：
  - `audit_log`：`java_classes.class_name LIKE '%BuildAuditLog%'` 且 L1 5 级包前缀白名单命中
  - `convertor`：`java_classes.class_name = '<identifier>Convertor'`
  - `notification`：extends / implements `AbstractIdentityActionNotificationParamCollector` + pkg5 命中
  - `ag_notification`：extends / implements `AbstractCallBackAGParameterMessageEvent`，pkg5 OR 类名含 identifier 关键词
  - `notification_resolver`：extends / implements `AbstractNotificationResolverAdaptor`，pkg5 OR 类名含 identifier 关键词
  - `party_collector`：extends / implements `ReceiverPartyCollector` 或 `InitiatorParentPartyCollector` + pkg5 命中
  - `bridge_sibling`：L1 中所有 `bridge.` 父包前缀下，`package_name LIKE '<parent>.%' AND implements_interfaces LIKE '%BusinessLogic%'`

#### Scenario: REF_CHAIN 递归
- **WHEN** `logic_steps.logic_type = 'REF_CHAIN'` 且 `bridges.bridge_id` 引用另一 chain_id
- **THEN** 系统 SHALL 递归展开被引用的 chain_id，循环 visited 集合防环
- **THEN** 递归深度 SHALL 由 `maxDepth` 上限保护

#### Scenario: 动态 chain 发现（Fix-E）
- **WHEN** `java_classes.method_bodies` 或 `source_text` 字段存在
- **THEN** 系统 SHALL 扫描 L1 + L2 + 特殊类 FQN 的源码，正则匹配 `setChainId\s*\(\s*"([^"]+)"`，提取动态 chain_id
- **THEN** 若新 chain_id 不在已有 `all_chain_ids` 中，重跑 chain 展开与 BFS
- **WHEN** `method_bodies` / `source_text` 字段不存在
- **THEN** 系统 SHALL 静默跳过该步骤，并向 `warnings` 追加 `"Dynamic chain scan skipped: <reason>"`

#### Scenario: import 图 BFS 截断
- **WHEN** import 图 BFS 累计节点数 ≥ 5000
- **THEN** 系统 SHALL 截断 BFS 并向 `warnings` 追加 `"Import BFS truncated at max_nodes=5000"`

#### Scenario: 可选的资源目录扫描（Plan B 核心）
- **WHEN** 调用 `search_service_impact` 时传入 `codeBaseRoot` 参数（非 None、非空字符串）
- **THEN** 系统 SHALL 验证 `codeBaseRoot`：
  - 必须是绝对路径（`os.path.isabs`）
  - 必须存在且是目录（`os.path.isdir`）
  - 校验失败 MUST 抛 `ValueError`
- **WHEN** 验证通过
- **THEN** 系统 SHALL 调用 `_scan_resource_files(codeBaseRoot, xml_files)`，复用 `analyzer.py:scan_resource_files`（line 593-616）逻辑：
  - 同样的 `_TARGET_DIRS = {"module-parameter", "namingsql"}`
  - 对每个 xml_path 找 `\\resources\\` 之前的根
  - `os.walk(root/resources/)` + dirname 白名单扫描
  - `os.path.relpath` 相对化（相对 `codeBaseRoot`）
- **THEN** 扫描得到的资源 XML SHALL 合并到 `files` 集合
- **WHEN** 扫描过程中 `os.walk` 抛错
- **THEN** 系统 SHALL 跳过该路径并向 `warnings` 追加 `"Resource directory scan failed at <path>: <error>"`

#### Scenario: 资源目录扫描未启用
- **WHEN** 调用 `search_service_impact` 时未传 `codeBaseRoot`（默认 None）
- **THEN** 系统 SHALL 跳过资源目录扫描
- **THEN** `files` 集合仅由 SQL 收集与 ER 遍历结果构成
- **THEN** 系统 MAY 向 `warnings` 追加 `"Resource directory scan skipped: codeBaseRoot not provided"`（仅当其他路径都未产生资源目录 XML 时）

#### Scenario: 签名与返回结构兼容
- **WHEN** 调用 `search_service_impact` 时不传新参数
- **THEN** 入参签名 MUST 扩展为：`schema, commandId=None, flowId=None, direction="both", maxDepth=20, codeBaseRoot=None`
- **THEN** 现有 4 个必填/默认参数的位置 MUST 不变
- **THEN** `direction` / `maxDepth` 仍做参数校验但**当前实现不使用**——`files` 集合完全由 `_explore_phase` + `_scan_resource_files` 决定
- **THEN** `direction='backward'` 与 `direction='forward'` 返回相同的 `files` 集合（不区分方向）
- **THEN** `codeBaseRoot` 为新增可选参数，向后兼容（老调用方不传此参数时行为不变）
- **THEN** 返回 JSON MUST 仍含 `entryPoint / direction / totalImpacted / files / impactChain / warnings`
- **THEN** `impactChain` MUST 为空列表（`_explore_phase` 不产出 edge 列表，保留字段语义以备未来扩展）

#### Scenario: schema 作为数据源切换器
- **WHEN** `schema` 参数指向 1.0Base 索引
- **THEN** 系统 SHALL 返回该 1.0Base 索引命中的所有 file_path / xml_path
- **WHEN** `schema` 参数指向 2.0Base 索引
- **THEN** 系统 SHALL 返回该 2.0Base 索引命中的所有 file_path / xml_path
- **WHEN** `schema` 参数指向公共库索引
- **THEN** 系统 SHALL 返回该公共库索引命中的所有 file_path / xml_path
- **THEN** 系统 MUST NOT 对 `files` 集合做任何基线过滤（不按 `1.0Base` / `2.0Base` / `Core_CFSC` / `Core_CBSC` / `GSD` 等路径前缀过滤）

#### Scenario: 1.0Base 完整文件集验证（仅适用于固定入口 commandId='ReleaseOrgOperatorCCSuspendStatus'）

⚠️  **本 Scenario 是事实性断言，不是通用契约。** `ReleaseOrgOperatorCCSuspendStatus.txt`
的 17 行清单**只**适用于 `commandId='ReleaseOrgOperatorCCSuspendStatus'` 这一个
固定入口；其它 commandId 的 files 集合不保证与该 17 行有任何特定关系。

- **WHEN** 调用 `search_service_impact(schema="<1.0Base_schema>", commandId="ReleaseOrgOperatorCCSuspendStatus", codeBaseRoot="<1.0BaseMaster 根>")`
- **THEN** `files` 列表 MUST 包含 `ReleaseOrgOperatorCCSuspendStatus.txt` 中列出的 17 个 1.0Base 路径（去重后）
- **THEN** `files` 列表 MUST 包含：
  - 2 个 audit_log 类的 `.java` 文件
  - 1 个 `{commandId}Convertor.java`
  - 1 个 party_collector 类的 `.java` 文件
  - 1 个 bridge_sibling 类的 `.java` 文件
  - 2 个 `module-parameter/*.xml` 文件
  - 1 个 `namingsql/*.xml` 文件
- **WHEN** 调用方**不**传 `codeBaseRoot`
- **THEN** `files` 列表 MUST 仍包含上述除 3 个资源目录 XML 之外的全部 14 行
- **THEN** 3 个资源目录 XML 是否出现 MUST 取决于索引器是否已将其路径收录到 `module_parameters` / `logics` / `beans` 等表的 `xml_path` 字段
- **WHEN** 其它 commandId（不是 `ReleaseOrgOperatorCCSuspendStatus`）
- **THEN** 本 Scenario 的「14/17 行」数字断言**不**适用；仅通用契约（入参兼容 / `files` 是 `schema` 命中的所有路径 / 资源目录扫描行为）继续生效
