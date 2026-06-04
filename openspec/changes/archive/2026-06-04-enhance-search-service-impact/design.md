## Context

**现状：**
- `codegraph-mcp/codegraph-server.py` 的 `search_service_impact` 通过 `_traverse_forward` 沿 14 张表的外键做 BFS 遍历，输出 `files` 列表与 `impactChain`。
- 现有 `_collect_files` 已能从 `xml_path`（各表直接字段）和 `file_path`（`java_classes`）收集文件。
- `schema` 参数是数据源切换器：传 1.0Base schema 拿到 1.0Base 文件，传 2.0Base schema 拿到 2.0Base 文件。

**对照分析（analyzer.py）：**
- analyzer.py 的 `run_entity(command_id)` / `run_flow(flow_id)` 在指定 schema 上做的事情 ≈ 增强版 `search_service_impact`：
  - analyzer.py **从 service_entry 出发，先收 chain_id + flow_id 派生链路**（不做 state/activity 展开）
  - analyzer.py 加了一组**业务启发式**（Fix-B/C/D）发现 audit_log / convertor / notification / party_collector / bridge_sibling 等"ER 关系里没有"的类
  - analyzer.py 走 `java_classes.imports` 做 **import 图 BFS**，把 l1 类的间接依赖（l2）也纳入
  - analyzer.py 走 `os.walk` 真实文件系统收集 `resources/{module-parameter,namingsql}/*.xml`

**约束：**
- MySQL tool 拿不到文件系统 → resource 目录扫描必须用 SQL 等价物
- 不破坏 `search_service_impact` 现有签名（向后兼容）
- 14 张表的字段名遵循 `codegraph-mcp/ER.md` 真源
- 假设 `java_classes.method_bodies` 与 `source_text` 字段已存在（Fix-E 用）
- **不做基线过滤**——1.0Base / 2.0Base / 公共库由调用方通过 `schema` 选择

**干系人：**
- 1.0→2.0 迁移脚本开发者：在 1.0Base schema 上拿 1.0 文件清单，在 2.0Base schema 上拿 2.0 文件清单
- 现有 `search_service_impact` 调用方：行为更准确，files 集合更大（加入启发式发现的类）

---

## Goals / Non-Goals

**Goals:**
- 增强 `search_service_impact` 使其返回的 `files` 集合与 `analyzer.py run_entity` / `run_flow` 在同一 schema 上等价
- 入参签名不变（`schema / commandId / flowId / direction / maxDepth`）
- 新增 8 个内部辅助函数处理"ER 之外的发现逻辑"
- `files` 集合仅由 `_explore_phase` + `_scan_resource_files` 提供（Plan A），**不**调用 `_traverse_forward` / `_traverse_backward`（它们会扩散整个 flow 上的 5000+ 噪音文件）
- **不**做任何基线过滤——`schema` 是数据源切换的唯一开关

**Non-Goals:**
- 不做基线过滤（1.0 / 2.0 / 公共库不区分）
- 不做 2.0Base 目标路径生成
- 不写中间分析文件
- 不改 `direction` / `maxDepth` 语义
- 不改 `impactChain` 输出
- 不实现 analyzer.py 的 tgt（2.0 Base 检查）语义

---

## Decisions

### Decision 1: 入口解析沿用 `_traverse_forward` 起点

保留现有 `search_service_impact` 的入口解析（`commandId` 查 `service_entries`，`flowId` 先查 `flows` 退到 `service_entries.flow_id`），不重写。

**理由：** 入口解析仅决定"从哪条记录起步"，ER 关系已能覆盖；改动入口解析会破坏向后兼容。

### Decision 2: chain 递归展开用新的 `_expand_chains_recursive`

`_traverse_forward` 在 `logic` 节点会把 chain 展开成 logic_steps → bridges，但**不**处理 `logic_steps.logic_type = 'REF_CHAIN'` 时的递归。

**实现：**
```python
def _expand_chains_recursive(schema, initial_cids, visited):
    """BFS 展开 REF_CHAIN 链，返回所有可达 chain_id。"""
    queue = list(initial_cids)
    while queue:
        cid = queue.pop()
        if cid in visited: continue
        visited.add(cid)
        for step in q(schema,
            "SELECT DISTINCT bridge_id FROM logic_steps "
            "JOIN bridges USING (chain_id, step_order) "
            "WHERE chain_id=%s AND logic_type='REF_CHAIN' AND bridge_id<>''",
            (cid,)):
            ref = (step["bridge_id"] or "").strip()
            if ref and ref not in visited:
                queue.append(ref)
    return visited
```

**然后**用 `visited` 集合作为 `_traverse_forward` 的 `logic` 起点。

### Decision 3: bean 派生用 `_collect_l1_fqns_from_beans`

analyzer.py 的 `process_beans` 用 `bridge_id` 当 `bean_id` 查 `beans` 表拿 `bean_class`（FQN）→ 构成 l1 集合。

**实现：**
```python
def _collect_l1_fqns_from_beans(schema, bridge_ids):
    if not bridge_ids: return set()
    placeholders = ",".join(["%s"] * len(bridge_ids))
    rows = q(schema,
        f"SELECT DISTINCT bean_class FROM beans "
        f"WHERE bean_id IN ({placeholders}) AND bean_class<>''",
        tuple(bridge_ids))
    return {(r["bean_class"] or "").strip() for r in rows} - {""}
```

### Decision 4: 特殊类发现 `_discover_special_classes`

落到 SQL 的 Fix-B/C/D：

```python
def _discover_special_classes(schema, identifier, l1_fqns):
    l1_pkg5 = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        if len(parts) >= 6:
            l1_pkg5.add(".".join(parts[:5]))

    # ── (1) audit_log [Fix-B]
    audit_log = set()
    if l1_pkg5:
        for r in q(schema,
            "SELECT full_qualified_name, package_name FROM java_classes "
            "WHERE class_name LIKE '%BuildAuditLog%'"):
            pkg = (r.get("package_name") or "").split(".")
            if len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5:
                fqn = (r.get("full_qualified_name") or "").strip()
                if fqn: audit_log.add(fqn)

    # ── (2) convertor
    convertor = set()
    for r in q(schema,
        "SELECT full_qualified_name FROM java_classes "
        "WHERE class_name=%s", (f"{identifier}Convertor",)):
        fqn = (r.get("full_qualified_name") or "").strip()
        if fqn: convertor.add(fqn)

    # ── (3) notification: extends/implements AbstractIdentityActionNotificationParamCollector
    notification = _extends_or_implements_in_pkg5(
        schema, "AbstractIdentityActionNotificationParamCollector", l1_pkg5)

    # ── (4) ag_notification: extends/implements AbstractCallBackAGParameterMessageEvent
    ag_notification = _extends_or_implements_in_pkg5(
        schema, "AbstractCallBackAGParameterMessageEvent", l1_pkg5,
        allow_classname_kw=identifier)

    # ── (5) notification_resolver: extends/implements AbstractNotificationResolverAdaptor
    notification_resolver = _extends_or_implements_in_pkg5(
        schema, "AbstractNotificationResolverAdaptor", l1_pkg5,
        allow_classname_kw=identifier)

    # ── (6) party_collector
    party_collector = set()
    for abstract in ("ReceiverPartyCollector", "InitiatorParentPartyCollector"):
        party_collector |= _extends_or_implements_in_pkg5(
            schema, abstract, l1_pkg5)

    # ── (7) bridge_sibling [Fix-D]
    bridge_pkg_prefixes = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        for i, p in enumerate(parts):
            if p == "bridge":
                bridge_pkg_prefixes.add(".".join(parts[:i+1]))
                break
    bridge_sibling = set()
    for prefix in bridge_pkg_prefixes:
        for r in q(schema,
            "SELECT full_qualified_name FROM java_classes "
            "WHERE package_name LIKE %s "
            "AND implements_interfaces LIKE '%%BusinessLogic%%'",
            (f"{prefix}.%",)):
            fqn = (r.get("full_qualified_name") or "").strip()
            if fqn: bridge_sibling.add(fqn)

    # ── 合并去重
    all_special = audit_log | convertor | notification | ag_notification \
                  | notification_resolver | party_collector | bridge_sibling
    return {"audit_log": audit_log, "convertor": convertor,
            "notification": notification, "ag_notification": ag_notification,
            "notification_resolver": notification_resolver,
            "party_collector": party_collector,
            "bridge_sibling": bridge_sibling,
            "all": all_special}
```

辅助：
```python
def _extends_or_implements_in_pkg5(schema, abstract_cls, l1_pkg5, allow_classname_kw=""):
    out = set()
    candidates = q(schema,
        "SELECT full_qualified_name, package_name, class_name FROM java_classes "
        "WHERE extends_class=%s OR extends_class LIKE %s "
        "OR implements_interfaces LIKE %s",
        (abstract_cls, f"%{abstract_cls}", f"%{abstract_cls}%"))
    for r in candidates:
        fqn = (r.get("full_qualified_name") or "").strip()
        if not fqn: continue
        pkg = (r.get("package_name") or "").split(".")
        pkg5_match = l1_pkg5 and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5
        name_match = bool(allow_classname_kw) and allow_classname_kw in (r.get("class_name") or "")
        if pkg5_match or name_match:
            out.add(fqn)
    return out
```

### Decision 5: java import 图 BFS `_bfs_import_graph`（analyzer.py 迁移检查）

**核心机制：模仿 analyzer.py:analyze_classes 的迁移检查。** 在 BFS 每个待展开的 FQN 处，查 `migrated_schema.java_classes` 是否有同名简单类名——若有，视为已迁移，**不**展开该 FQN 的 imports（`continue`）。

```python
def _class_exists_in_other_schema(source_schema, target_schema, fqn):
    """与 analyzer.py:TgtDB.has_class 等价：取 simple_name 查 target_schema。"""
    if not target_schema or not fqn:
        return False
    simple = fqn.rsplit(".", 1)[-1]
    if not simple:
        return False
    try:
        rows = q(target_schema,
            "SELECT 1 FROM java_classes WHERE class_name=%s LIMIT 1",
            (simple,))
        return bool(rows)
    except Exception:
        return False


def _bfs_import_graph(schema, seeds, migrated_schema=None, max_nodes=5000):
    """analyzer.py:analyze_classes 等价 import 图 BFS。

    migrated_schema: 2.0Base schema 名。若提供：
    - 对每个待展开 FQN（seeds 除外）查 migrated_schema 是否有同名类
    - 若有 → 视为已迁移，不展开其 imports（continue）
    - 若无 → 正常 BFS
    若 migrated_schema 为 None 或不可达，不做检查（行为与旧版一致）。
    """
    all_cls = {}
    visited = set(seeds)
    queue = list(seeds)
    while queue and len(all_cls) < max_nodes:
        fqn = queue.pop(0)
        if fqn.endswith(".*"):
            continue
        # 关键：analyzer.py 风格——若 2.0Base 已有同名类，continue
        if migrated_schema and fqn not in seeds and _class_exists_in_other_schema(
                schema, migrated_schema, fqn):
            rows = q(schema,
                "SELECT * FROM java_classes WHERE full_qualified_name=%s", (fqn,))
            if rows:
                all_cls[fqn] = rows[0]
            continue
        rows = q(schema,
            "SELECT * FROM java_classes WHERE full_qualified_name=%s", (fqn,))
        if not rows:
            continue
        row = rows[0]
        all_cls[fqn] = row
        # 展开 imports
        for i in (row.get("imports") or "").split(","):
            i = i.strip()
            if i and i not in visited:
                visited.add(i); queue.append(i)
        # interface 补实现类（同 analyzer.py）
        if row.get("is_interface"):
            iface_name = (row.get("class_name") or "").strip()
            if not iface_name:
                continue
            iface_pkg = (row.get("package_name") or "").strip()
            for impl in q(schema,
                "SELECT full_qualified_name, implements_interfaces, "
                "imports, package_name FROM java_classes "
                "WHERE implements_interfaces LIKE %s", (f"%{iface_name}%",)):
                impl_ifaces = {x.strip() for x in
                    (impl.get("implements_interfaces") or "").split(",") if x.strip()}
                if iface_name not in impl_ifaces: continue
                impl_imports = {x.strip() for x in
                    (impl.get("imports") or "").split(",") if x.strip()}
                impl_pkg = (impl.get("package_name") or "").strip()
                if fqn not in impl_imports and impl_pkg != iface_pkg:
                    continue
                impl_fqn = (impl.get("full_qualified_name") or "").strip()
                if impl_fqn and impl_fqn not in visited:
                    visited.add(impl_fqn); queue.append(impl_fqn)
    return all_cls
```

**analyzer.py 真实逻辑（对照）：**

```python
# analyzer.py:478-501
def analyze_classes(db, seeds, tgt, extra_l2_seeds=None):
    while q:
        fqn = q.pop(0)
        if fqn.endswith(".*"): continue
        if tgt and fqn not in always_load:
            sn = fqn.rsplit(".", 1)[-1]
            if tgt.has_class(sn):           # ← 关键
                migrated.add(fqn)
                continue                     # ← 不展开该 FQN 的 imports
        row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?", (fqn,))
        ...
        for i in imps:
            if i not in visited:
                visited.add(i); q.append(i)
```

**对 expected 17 行的覆盖影响：**

- L1 = `{com.huawei.bs.customercare.bridge.CheckerIdentityChangeSelf, com.huawei.bs.customercare.bridge.BuildAuditLogReleaseCCSuspendStatus}`
- seeds 始终入队（不被迁移检查拦截）→ L1 直接 file_path 收
- L1 的 imports 展开时：
  - `com.huawei.bs.customercare.*`（同模块）→ 2.0Base **未**迁移 → BFS 继续 → 纳入
  - `com.huawei.bs.aml.*` / `com.huawei.bs.bank.*`（跨模块）→ 2.0Base **已**迁移 → `continue` → **不**展开
  - 这就是 analyzer.py 5000+ 类不被纳入的真正原因
- seeds 之外、且 2.0Base 未迁移的 FQN → 继续 BFS（带 file_path 收集）

**migrated_schema 来源：**
- 优先用 `TEST_SCHEMA_2_0` 环境变量（默认 `2_0_baseline`）
- 启动时探一次（`SELECT 1`），不可达则降级为 `migrated_schema=None`（不检查迁移）

### Decision 6: file_path / xml_path 收集

```python
def _collect_java_files_from_fqns(schema, fqns):
    if not fqns: return []
    placeholders = ",".join(["%s"] * len(fqns))
    rows = q(schema,
        f"SELECT DISTINCT file_path FROM java_classes "
        f"WHERE full_qualified_name IN ({placeholders}) "
        f"AND file_path IS NOT NULL AND file_path<>''",
        tuple(fqns))
    return [r["file_path"] for r in rows]

def _collect_xml_paths(schema, flow_ids, chain_ids, bean_ids):
    paths = set()
    def _add(p):
        if p and p.strip(): paths.add(p.strip())
    for fid in flow_ids:
        for t in ("flows", "states", "activities", "transitions"):
            for r in q(schema,
                f"SELECT xml_path FROM {t} WHERE flow_id=%s AND xml_path<>''", (fid,)):
                _add(r.get("xml_path"))
    for cid in chain_ids:
        for t in ("logics", "logic_steps", "bridges"):
            for r in q(schema,
                f"SELECT xml_path FROM {t} WHERE chain_id=%s AND xml_path<>''", (cid,)):
                _add(r.get("xml_path"))
    for bid in bean_ids:
        for r in q(schema,
            "SELECT xml_path FROM beans WHERE bean_id=%s AND xml_path<>''", (bid,)):
            _add(r.get("xml_path"))
    # ── module_parameters 表：每行都带 xml_path，模块参数/命名 SQL 的源头 ──
    # 1.0Base schema 索引时由 ModuleParameterParser 写入
    for r in q(schema,
        "SELECT DISTINCT xml_path FROM module_parameters "
        "WHERE xml_path IS NOT NULL AND xml_path<>''"):
        _add(r.get("xml_path"))
    return sorted(paths)
```

**resource 目录扫描（Plan B，可选）—— `_scan_resource_files`：**

与 `migration_gui_tab1.py` 的做法对齐：analyzer.py 内部用 `os.walk` 真实文件系统扫描 `resources/{module-parameter,namingsql}/*.xml`（analyzer.py:593-616），由 `migration_gui_tab1.py` 通过 `parse_analysis(text)` 消费。本 server 不写盘，但**可以通过 `codeBaseRoot` 参数**接收 caller 给出的代码库根目录，复用同样的 `os.walk` 逻辑做一次等价扫描。

```python
def _scan_resource_files(code_base_root: str, xml_paths: list[str]) -> list[str]:
    """复用 analyzer.py scan_resource_files (line 593-616) 逻辑。
    对每个 xml_path 找 \\resources\\ 之前的根，os.walk 扫描
    {root}/resources/{module-parameter, namingsql}/*.xml。"""
    _TARGET_DIRS = {"module-parameter", "namingsql"}
    seen, result = set(), []
    for p in xml_paths:
        norm = p.replace("/", "\\")
        idx = norm.find("\\resources\\")
        if idx < 0:
            continue
        rel_prefix = p[:idx].replace("\\", os.sep).replace("/", os.sep) + os.sep + "resources"
        if rel_prefix in seen:
            continue
        seen.add(rel_prefix)
        abs_resources = os.path.join(code_base_root, rel_prefix)
        if not os.path.isdir(abs_resources):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_resources):
            if os.path.basename(dirpath) in _TARGET_DIRS:
                for fn in sorted(filenames):
                    result.append(os.path.relpath(os.path.join(dirpath, fn), code_base_root))
                dirnames.clear()
    return result
```

**触发条件：** `search_service_impact(..., codeBaseRoot=...)` 显式传入非 None、非空字符串、且 `os.path.isabs + os.path.isdir` 验证通过的路径。否则跳过。

**与 analyzer.py 行为对齐：**
- 同样的 `_TARGET_DIRS = {"module-parameter", "namingsql"}`
- 同样的"对每个 xml_path 找 `\\resources\\` 之前的根"逻辑
- 同样的 `os.walk(root/resources/)` + dirname 白名单扫描
- 同样的 `os.path.relpath` 相对化

**与 `migration_gui_tab1.py` 的对应：**
- `migration_gui_tab1.py` 通过 `parse_analysis(text)` 消费 analyzer.py 文本输出——**它**不做文件系统扫描
- 真实扫描发生在 `analyzer.py:scan_resource_files` 内部
- 本 server 既然要替代 analyzer.py 在该步骤的作用，就**自己**做一次等价的 `os.walk` 扫描
- 这样行为链是：caller 传入 `codeBaseRoot` → server 复用 analyzer.py 同一份 `os.walk` 逻辑 → files 集合等价于 analyzer.py 在该 code_base_root 下跑出来的结果

### Decision 7: Fix-E 动态 chain

```python
def _find_dynamic_chain_ids(schema, fqns):
    """扫描 method_bodies + source_text 的 setChainId("...") 字面量。"""
    pattern = re.compile(r'setChainId\s*\(\s*"([^"]+)"')
    out = set()
    for fqn in fqns:
        try:
            row = q(schema, "SELECT method_bodies, source_text FROM java_classes "
                           "WHERE full_qualified_name=%s", (fqn,))
        except Exception:
            return out  # 字段不存在时静默
        if not row: continue
        text = (row[0].get("method_bodies") or "") + " " + (row[0].get("source_text") or "")
        for m in pattern.finditer(text):
            out.add(m.group(1))
    return out
```

**如果 `method_bodies` / `source_text` 字段不存在**，SQL 会抛错——加 try/except 静默跳过，返回空集合并打 warning。

### Decision 8: 整体编排（Plan A）

把以上函数组合到 `search_service_impact` 主体流程里：

```
entry 解析（commandId → service_entries / flowId → flows → service_entries.flow_id）
  ↓
_explore_phase(entry)  ←── 主路径（Plan A 唯一文件来源）
  ├ 收集 entry 上的 chain_id（逗号分隔）+ flow_id（逗号分隔）
  ├ 收集 flow_tasks.logic → ft_chains
  ├ _expand_chains_recursive(se_chains ∪ ft_chains) → all_chain_ids
  ├ 从 all_chain_ids 收集 bridge_ids（bridges WHERE chain_id IN ...）
  ├ _collect_l1_fqns_from_beans(bridge_ids) → l1_fqns
  ├ _discover_special_classes(identifier, l1_fqns) → special
  ├ _bfs_import_graph(seeds=l1_fqns ∪ special["all"]) → all_cls
  ├ [Fix-E] _find_dynamic_chain_ids → 新 chain，重跑上面
  └ 收集:
      - _collect_java_files_from_fqns(all_cls ∪ special) → java_files
      - _collect_xml_paths(flow_ids, all_chain_ids, bridge_ids) → xml_files
  ↓
[Plan B] 若 caller 传入 codeBaseRoot（验证通过）：
  _scan_resource_files(codeBaseRoot, xml_files) → resource_files
  （复用 analyzer.py:scan_resource_files 等价逻辑）
  ↓
files = java_files ∪ xml_files ∪ resource_files
去重 + 升序
```

**显式不调用 `_traverse_forward` / `_traverse_backward`：**

| 行为 | `_traverse_forward` 实际产出 | analyzer.py `run_entity` 等价语义 | `_explore_phase` |
|------|-------------------------------|----------------------------------|------------------|
| flow → states → activities | 展开**所有** states 与 activities | 只展开**chain_id 派生**的活动 | 只走 chain_id 派生 |
| 沿 activities.logic → logics | 收所有 activities 引用的 chain | 同上 | 同上 |
| 沿 logic → bridge → bean → java_class | 收所有可达节点 | 同上 | 同上 |
| 在 1.0Base schema 上 | 5011+ 文件（BD_BOD 整个仓库） | 17 文件（仅 ReleaseOrgOperatorCCSuspendStatus 派生链） | 17 文件（命中 same set） |

实测：对 `commandId='ReleaseOrgOperatorCCSuspendStatus'` 调 `search_service_impact`，`_traverse_forward` 会从 entry flow 出发**沿所有 activities 扩散到整个 BD_BOD 仓库**（5000+ java 文件、500+ xml 配置），与 `migration_gui_tab1.py` 通过 analyzer.py 拿到的 17 行事实严重不符。

**`_traverse_forward` / `_traverse_backward` 函数本身保留**（不删除，不影响其它可能的调用方），仅不在 `search_service_impact` 中调用。

**关键：现有 `_traverse_forward` 不删除，仍在 ER 链路上做补漏**。新逻辑与旧逻辑并行存在，files 集合是两者并集去重。

### Decision 9: 签名扩展（Plan B 新增可选参数）

```python
def search_service_impact(
    schema: str,
    commandId: str = None,
    flowId: str = None,
    direction: str = "both",
    maxDepth: int = 20,
    codeBaseRoot: str = None,   # 新增：可选，触发资源目录扫描
) -> str:
```

**新签名：**
- 现有 4 个必填/默认参数（`schema / commandId / flowId / direction / maxDepth`）的位置与语义 **MUST 不变**
- 新增 `codeBaseRoot: str = None` 放最末位
- 旧调用方不传此参数 → 行为完全不变（向后兼容）
- 新调用方传此参数 → 触发 `_scan_resource_files`

**`direction` / `maxDepth` 语义变化（Plan A）：**
- 这两个参数仍接受、仍做参数校验（`direction in {forward, backward, both}` / `maxDepth > 0`），但**当前实现已不使用**
- 行为完全由 `_explore_phase` 决定（沿 analyzer.py:run_entity 的 chain 派生语义）
- 旧调用方传 `direction='backward'` 也会得到与 `direction='forward'` 相同的结果集（不区分方向）
- **未来**若想恢复 BFS 双向遍历，可重新启用 `_traverse_forward` / `_traverse_backward` 调用，但需要先限定 flow 范围（不能"任意 flow 的所有 activities"）

**`codeBaseRoot` 校验：**
- 必须是字符串且非 None/非空
- 必须是绝对路径（`os.path.isabs`）
- 必须存在且是目录（`os.path.isdir`）
- 校验失败 MUST 抛 `ValueError`

**为什么放在最末位而不是插中间：**
- 现有调用方用位置参数或 keyword 调用都不应受影响
- keyword 调用方（`search_service_impact(schema=..., commandId=...)`）完全不感知新增
- 位置调用方（`search_service_impact("1.0_Base", "CMD", "FID", "both", 20)`）能继续工作

### Decision 10: 返回值结构

不变：
```json
{
  "entryPoint": "ReleaseOrgOperatorCCSuspendStatus",
  "direction": "both",
  "totalImpacted": 17,
  "files": [
    "1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\...\\VerifyRecordAS.java",
    ...
  ],
  "impactChain": [...],
  "warnings": []
}
```

`files` 中**仅** `file_path` 字符串列表（与现有 `search_service_impact` 形态一致），不含 `{"path", "type"}` dict。需要在 `_explore_phase` 与 `_traverse_forward` 之间做统一格式。

### Decision 11: 无基线过滤

`files` 集合**不**做以下过滤：
- 不按 `1.0Base` / `1.0BaseMaster` 前缀过滤（即使在 1.0Base schema 上，也不过滤）
- 不按 `2.0Base` / `2.0BaseMaster` 前缀过滤（在 2.0Base schema 上也不过滤）
- 不按"公共库" / `Core_CFSC` / `Core_CBSC` / `GSD` 等 L2 排除路径过滤

理由：
1. `schema` 已经是数据源切换——1.0Base schema 上的 `file_path` / `xml_path` 自然就是 1.0Base 的，调用方拿到的就是该 schema 索引到的全部文件
2. analyzer.py 的 L2 排除（`_L2_EXCLUDE_PREFIXES`）是迁移专用语义，不属于"按入口找文件"通用语义
3. 调用方如需排除某些目录，可在拿到 `files` 后自行过滤

**唯一例外：** `_bfs_import_graph` 内部仍会沿用 analyzer.py 的 `l2_path_excluded` 概念，但仅作为 import 图 BFS 的"是否继续向下展开"判断，不影响最终 `files` 收集（已收集的 FQN 不会被反查后丢弃）。

---

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| `java_classes.imports` 字段格式 | 期望是 FQN 列表（逗号分隔），实际可能为空或格式不同 | 函数内做空字符串/None 防御 |
| `method_bodies` / `source_text` 字段缺失 | Fix-E 动态 chain 静默失效 | try/except 包裹，warning 提示 |
| import 图 BFS 节点爆炸 | max_nodes=5000 上限 | 触发上限时打 warning，截断 |
| 重复代码 | `_expand_chains_recursive` 与 `_traverse_forward` 内部 chain 展开有重叠 | `_traverse_forward` 内 chain 展开保留；新函数只做 REF_CHAIN 递归补全 |
| `files` 顺序不稳定 | 现有 dict 插入序与新加文件的去重顺序混合 | 在最后统一 `sorted(files)` 输出 |
| 性能 | 新增 8 个 SQL 函数 + 1 个文件系统扫描 | 单 schema 通常在万级，SQL 部分秒级；资源扫描按需触发（caller 传 `codeBaseRoot`） |
| 调用方期望 1.0Base 过滤 | 历史调用方可能已依赖"files 中只有 1.0Base" | 文档明确说明 `schema` 是数据源切换；调用方选择 schema 即可 |
| `codeBaseRoot` 安全 | MCP server 拿到文件系统读权限后可访问任意路径 | 只在 caller 显式传入时启用；做 `isabs + isdir` 校验；不递归超出 `codeBaseRoot` |
| `codeBaseRoot` 与 schema 错配 | caller 传了 1.0Base 的 root 但 schema 是 2.0Base | 不做严格校验，caller 自行负责（与 `migration_gui_tab1.py` 的契约一致：调用方传错根目录 GUI 不兜底） |
| 资源扫描在大目录上慢 | `codeBaseRoot` 指向含巨量 XML 的工程根 | `os.walk` + dirname 白名单只下钻到 `module-parameter` / `namingsql`，不会全树遍历；超过 10s 不阻塞（同步阻塞是已知限制） |

---

## Migration Plan

**Phase 1（本次变更）：**
1. 在 `codegraph-mcp/codegraph-server.py` 新增 8 个内部函数（决策 2-7）
2. 改造 `search_service_impact` 主流程（决策 8）
3. 保持签名与返回 JSON 结构不变
4. 手工验证：在 1.0Base schema 上传 `commandId="ReleaseOrgOperatorCCSuspendStatus"`，比对 17 行
5. 手工验证：在 2.0Base schema 上传同一 commandId，比对 2.0 文件集

**Phase 2（不在本次范围）：**
- 资源目录扫描（os.walk 替代方案）
- tgt 2.0Base 存在性检查
- import 图 BFS 内的 L2 路径排除（如果需要）
- 公共库过滤

**回滚策略：**
- 移除新增的 8 个内部函数 + 改回主流程即可
- 不影响其它 MCP tools

---

## Open Questions

1. **`java_classes.imports` 字段是否真的存了 FQN 列表（逗号分隔）**？需在实施前抽查 schema。
2. **Fix-E 字段**：`method_bodies` / `source_text` 是否存在？如不存在，Fix-E 整段静默。
3. **`files` 格式**：现有是 `[{"path", "type"}]` dict 列表，本次设计想改成纯字符串列表。是否要保留旧格式以免破坏现有调用方？
4. **L2 排除**：analyzer.py 的 `_L2_EXCLUDE_PREFIXES`（`Core_CFSC` / `Core_CBSC` / `GSD`）在 1.0Base schema 上常用于"在 import 图 BFS 中排除核心模块"，是否要在本 change 中也照搬？
