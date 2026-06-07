#!/usr/bin/env python3
"""
analyzer_compat.py — analyzer.py 核心算法的 MySQL 兼容移植。

来源: D:\\2026\\backups\\AICodeMigrationKit0423\\TxnMigration\\FlowAndChainAnalyzer\\analyzer.py

改动要点:
  - SrcDB / TgtDB 由 SQLite 改为 MySQL(走 codegraph-server.py 的 q() 函数)
  - SQL 占位符由 ? 替换为 %s
  - CLI 入口 / 文件输出 / write_chains 等"分析报告写盘"部分**移除**——
    本模块只暴露核心数据收集逻辑,返回 (files, warnings, ...) 数据结构
  - 不依赖外部 SQLite 文件,直接读 MySQL schema(1.0Base / 2.0Base)

对外接口:
  - run_entity(schema, tgt_schema, command_id) -> dict
  - run_flow(schema, tgt_schema, flow_id) -> dict

返回 dict 结构:
  {
    "entry_point": str,                    # command_id or flow_id
    "files": list[str],                    # 全量 file_path 集合
    "l1_classes": list[str],               # bridge 派生的 FQN
    "l2_classes": list[str],               # import BFS 派生的 FQN
    "special_classes": dict[str, list[str]],
    "xml_files": list[str],
    "bridges": list[dict],                 # [{bridge_id, chain_id, step_order, before_beans}]
    "beans": list[dict],                   # [{bean_id, bean_class, xml_path}]
    "chains": list[str],
    "migrated_bridges": list[str],
    "warnings": list[str],
  }
"""

import os
import re
import sys
import io
from collections import OrderedDict


# ═══════════════════════════════════════════════════════════════════════
#  MySQL 数据库封装（与 analyzer.py: SrcDB / TgtDB 接口一致）
# ═══════════════════════════════════════════════════════════════════════

def _mysql_q(schema, sql, params=()):
    """MySQL 占位符转换: analyzer.py 用 ?,这里先替换为 %s 再调 codegraph_server.q()。

    在模块加载时由 __init__ 注入,避免直接 import codegraph_server 造成循环。"""
    raise RuntimeError("_mysql_q not bound; call __init__(q_fn) first")


class MySQLSrcDB:
    """analyzer.py:SrcDB 的 MySQL 等价。"""
    def __init__(self, schema, q_fn):
        self.schema = schema
        self.q = lambda sql, params=(): q_fn(self.schema, _sqlite_to_mysql(sql), params or ())

    def all(self, sql, params=()):
        try:
            return list(self.q(sql, params))
        except Exception:
            return []

    def first(self, sql, params=()):
        try:
            rows = self.q(sql, params)
            return rows[0] if rows else None
        except Exception:
            return None

    def exists(self, sql, params=()):
        return self.first(sql, params) is not None

    def class_fqns(self, name):
        return [r["full_qualified_name"] for r in self.all(
            "SELECT full_qualified_name FROM java_classes WHERE class_name=?", (name,))]

    def close(self):
        pass


class MySQLTgtDB:
    """analyzer.py:TgtDB 的 MySQL 等价。

    注:target_ms 路径过滤 (1.0BaseMaster/<target_ms>/...) 在 MySQL 端不实现——
    codegraph-server.py 的 schema 已经是 1.0Base/2.0Base 整库,无需按 ms 切分。
    因此 _path_ok 在 2.0Base schema 中一律 True;has_class 直接按 class_name 查。
    """
    def __init__(self, schema, q_fn, target_ms=None):
        self.schema = schema
        self.q = lambda sql, params=(): q_fn(self.schema, _sqlite_to_mysql(sql), params or ())

    def _ex(self, sql, p=()):
        try:
            return bool(self.q(sql, p))
        except Exception:
            return False

    def has_flow(self, fid):
        return self._ex("SELECT 1 FROM flows WHERE flow_id=?", (fid,))

    def has_flow_rfid(self, rfid):
        return self._ex("SELECT 1 FROM flows WHERE real_flow_id=?", (rfid,))

    def has_chain(self, cid):
        return self._ex("SELECT 1 FROM logic_steps WHERE chain_id=?", (cid,))

    def has_bridge(self, bid):
        return self._ex("SELECT 1 FROM bridges WHERE bridge_id=?", (bid,))

    def has_bridge_fuzzy(self, bid):
        return self.has_bridge(bid) or (
            bid.startswith("BS.") and self.has_bridge(bid[3:]))

    def has_bean(self, bid):
        return self._ex("SELECT 1 FROM beans WHERE bean_id=?", (bid,))

    def has_bean_fuzzy(self, bid):
        return self.has_bean(bid) or (
            bid.startswith("BS.") and self.has_bean(bid[3:]))

    def has_class(self, name):
        return self._ex("SELECT 1 FROM java_classes WHERE class_name=?", (name,))

    def class_fqns(self, name):
        return [r["full_qualified_name"] for r in self.all(
            "SELECT full_qualified_name FROM java_classes WHERE class_name=?", (name,))]

    def has_component_bean(self, bid: str) -> bool:
        """[Fix-A] 1.0 中通过 XML 显式注册的 bean 在 2.0 中可能改为 @Component 自动注册。

        取 bridge_id 最后一段大写开头的 token(类名)查 2.0 java_classes。
        """
        simple = bid.split(".")[-1]
        if not simple or not simple[0].isupper():
            return False
        return self.has_class(simple)

    def all(self, sql, params=()):
        try:
            return list(self.q(sql, params))
        except Exception:
            return []

    def close(self):
        pass


def _sqlite_to_mysql(sql: str) -> str:
    """? -> %s（占位符转换）。

    analyzer.py 大量使用 `f"%BusinessLogic%"` / `f"%{abstract_cls}%"` 等 LIKE 模式。
    在 SQLite 里 % 是 LIKE 通配符，但 MySQL 也认——只是 PyMySQL 的 execute 会
    把 % 当占位符前缀。**为避免冲突，所有 LIKE 模式必须在调用前用具体
    placeholder 替换或在 SQL 里硬编码**。本函数只做 ? → %s 转换。
    """
    return sql.replace("?", "%s")


# ═══════════════════════════════════════════════════════════════════════
#  工具函数（与 analyzer.py: line 145-150 等价）
# ═══════════════════════════════════════════════════════════════════════

_L2_EXCLUDE_PREFIXES = (
    "1.0BaseMaster\\Core_CFSC",
    "1.0BaseMaster\\Core_CBSC",
    "1.0BaseMaster\\GSD",
    "1.0BaseMaster/Core_CFSC",
    "1.0BaseMaster/Core_CBSC",
    "1.0BaseMaster/GSD",
)

# 包前缀 L2 排除（用于 BFS 内部，避免进入平台/工具根包子图）
# 与 _L2_EXCLUDE_PREFIXES 互补：后者过滤 file_path/xml_path 路径，
# 前者过滤 java 包名（FQN 的 . 分隔前缀）。
_L2_PKG_EXCLUDE = (
    "com.huawei.bs.base.",
    "com.huawei.bs.order.",
    "com.huawei.bs.account.",
    "com.huawei.ds.",
    "com.huawei.payment.",
    "com.huawei.bs.framework.",
    "com.huawei.bs.bpm.",
    "com.huawei.bs.process.",
    "com.huawei.bs.service.",
    "com.huawei.bs.notification.",
)


def _is_l2_excluded(file_path: str) -> bool:
    if not file_path:
        return False
    n = file_path.replace("\\", "/")
    for p in _L2_EXCLUDE_PREFIXES:
        np = p.replace("\\", "/")
        if np in n:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════
#  chain / flow 展开（analyzer.py: line 172-260 等价）
# ═══════════════════════════════════════════════════════════════════════

def expand_flows(db, root_id, tgt):
    result, visited, migrated = OrderedDict(), set(), set()
    q = [root_id]
    while q:
        fid = q.pop(0)
        if fid in visited:
            continue
        visited.add(fid)
        for row in db.all("SELECT * FROM flows WHERE flow_id=?", (fid,)):
            if fid not in result:
                result[fid] = row
            ref = (row.get("ref_template") or "").strip()
            if not ref or ref in visited:
                continue
            if tgt and fid != root_id and tgt.has_flow(ref):
                migrated.add(ref)
                visited.add(ref)
                for rr in db.all("SELECT * FROM flows WHERE flow_id=?", (ref,)):
                    if ref not in result:
                        result[ref] = rr
            else:
                q.append(ref)
    return result, migrated


def expand_chain(db, cid, visited, tgt):
    if cid in visited:
        return []
    visited.add(cid)
    covered = tgt and tgt.has_chain(cid)
    result = []
    for step in db.all("SELECT * FROM logic_steps WHERE chain_id=? ORDER BY step_order", (cid,)):
        lt = (step.get("logic_type") or "").upper()
        so = step.get("step_order")
        bridges, seen_b = [], set()
        for b in db.all(
                "SELECT * FROM bridges WHERE chain_id=? AND step_order=? ORDER BY bridge_order",
                (cid, so)):
            bid = (b.get("bridge_id") or "").strip()
            if b.get("is_skip") or bid in seen_b:
                continue
            if bid:
                seen_b.add(bid)
            bridges.append(b)
        if lt == "REF_CHAIN":
            for b in bridges:
                ref = (b.get("bridge_id") or "").strip()
                if ref and ref not in visited:
                    result.extend(expand_chain(db, ref, visited, tgt))
        elif not covered:
            for b in bridges:
                bb = (b.get("before_beans") or "").strip()
                if bb:
                    for x in bb.split(","):
                        x = x.strip()
                        if x:
                            result.append((cid, step, {
                                "bridge_id": x, "_is_before_bean": True
                            }))
                result.append((cid, step, {
                    k: v for k, v in b.items() if k != "before_beans"
                }))
    return result


def detect_overrides(db, flow_map, root_id, migrated):
    children = {}
    for fid, row in flow_map.items():
        ref = (row.get("ref_template") or "").strip()
        if ref and ref in flow_map:
            children.setdefault(ref, []).append(fid)

    def _desc(fid, vis=None):
        vis = vis or set()
        out = []
        for c in children.get(fid, []):
            if c in vis:
                continue
            vis.add(c)
            if c not in migrated:
                out.append(c)
            out.extend(_desc(c, vis))
        return out

    overrides = {}
    for fid in flow_map:
        desc = _desc(fid)
        if not desc:
            continue
        for act in db.all(
                "SELECT * FROM activities WHERE flow_id=? ORDER BY state_name, activity_order",
                (fid,)):
            logic = (act.get("logic") or "").strip()
            if not logic or (act.get("logic_type") or "chain").lower() != "chain":
                continue
            for cfid in desc:
                oid = f"{cfid}_{logic}"
                if db.exists("SELECT 1 FROM logic_steps WHERE chain_id=?", (oid,)):
                    overrides[oid] = {
                        "original_logic": logic,
                        "parent_flow_id": fid,
                        "child_flow_id": cfid,
                    }
    return overrides


# ═══════════════════════════════════════════════════════════════════════
#  Fix-B/C/D 特殊类发现（analyzer.py: line 263-452 等价）
# ═══════════════════════════════════════════════════════════════════════

def _best_match_by_id(items_dict, identifier):
    if not items_dict:
        return None
    if identifier in items_dict:
        return identifier
    cand = [(k, v) for k, v in items_dict.items() if k.startswith(identifier)]
    if len(cand) == 1:
        return cand[0][0]
    return identifier if identifier in items_dict else None


def find_special_classes(db, identifier, l1_fqns):
    """analyzer.py:263-414 等价。"""
    if not identifier:
        return {"audit_log": [], "convertor": [], "notification": [],
                "ag_notification": [], "notification_resolver": [],
                "party_collector": [], "bridge_sibling": []}

    l1_pkg5 = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        if len(parts) >= 6:
            l1_pkg5.add(".".join(parts[:5]))

    # ── (1) audit_log [Fix-B，但收敛到 entry 真正触达的]
    # analyzer.py 原始: class_name LIKE '%BuildAuditLog%' —— 太宽,会把同模块所有
    # BuildAuditLog* 都收进来(如 BuildAuditLogCloseCall/TakeACall/VerifyCaller)。
    # 与 17 行期望对比,这些 extra 类不属于 entry 业务影响。
    # 改为: 类名 = BuildAuditLog + entry identifier(且包前缀与 L1 一致)。
    audit_log = []
    if l1_pkg5 and identifier:
        target_audit = f"BuildAuditLog{identifier}"
        for r in db.all(
                "SELECT full_qualified_name, package_name FROM java_classes "
                "WHERE class_name=?", (target_audit,)):
            pkg = (r.get("package_name") or "").split(".")
            if len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5:
                fqn = (r.get("full_qualified_name") or "").strip()
                if fqn:
                    audit_log.append(fqn)

    # ── (2) convertor
    convertor = []
    for r in db.all(
            "SELECT full_qualified_name FROM java_classes "
            "WHERE class_name=?", (f"{identifier}Convertor",)):
        fqn = (r.get("full_qualified_name") or "").strip()
        if fqn:
            convertor.append(fqn)

    # ── (3) notification [Fix-C]
    notification = []
    if l1_pkg5:
        for r in db.all(
                "SELECT full_qualified_name, package_name, class_name FROM java_classes "
                "WHERE extends_class=? "
                "OR extends_class LIKE ? "
                "OR implements_interfaces LIKE ?",
                ("AbstractIdentityActionNotificationParamCollector",
                 "%AbstractIdentityActionNotificationParamCollector",
                 "%AbstractIdentityActionNotificationParamCollector%")):
            fqn = (r.get("full_qualified_name") or "").strip()
            if not fqn:
                continue
            pkg = (r.get("package_name") or "").split(".")
            if l1_pkg5 and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5:
                notification.append(fqn)

    # ── (4) ag_notification
    ag_notification = []
    if l1_pkg5 or identifier:
        for r in db.all(
                "SELECT full_qualified_name, package_name, class_name FROM java_classes "
                "WHERE extends_class=? "
                "OR extends_class LIKE ? "
                "OR implements_interfaces LIKE ?",
                ("AbstractCallBackAGParameterMessageEvent",
                 "%AbstractCallBackAGParameterMessageEvent",
                 "%AbstractCallBackAGParameterMessageEvent%")):
            fqn = (r.get("full_qualified_name") or "").strip()
            if not fqn:
                continue
            pkg = (r.get("package_name") or "").split(".")
            pkg5_match = l1_pkg5 and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5
            name_match = identifier and identifier in (r.get("class_name") or "")
            if pkg5_match or name_match:
                ag_notification.append(fqn)

    # ── (5) notification_resolver [Fix-C]
    notification_resolver = []
    if l1_pkg5 or identifier:
        for r in db.all(
                "SELECT full_qualified_name, package_name, class_name FROM java_classes "
                "WHERE extends_class=? "
                "OR extends_class LIKE ? "
                "OR implements_interfaces LIKE ?",
                ("AbstractNotificationResolverAdaptor",
                 "%AbstractNotificationResolverAdaptor",
                 "%AbstractNotificationResolverAdaptor%")):
            fqn = (r.get("full_qualified_name") or "").strip()
            if not fqn:
                continue
            pkg = (r.get("package_name") or "").split(".")
            pkg5_match = l1_pkg5 and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5
            name_match = identifier and identifier in (r.get("class_name") or "")
            if pkg5_match or name_match:
                notification_resolver.append(fqn)

    # ── (6) party_collector [Fix-C]
    party_collector = []
    if l1_pkg5:
        for abstract in ("ReceiverPartyCollector", "InitiatorParentPartyCollector"):
            for r in db.all(
                    "SELECT full_qualified_name, package_name, class_name FROM java_classes "
                    "WHERE extends_class=? OR extends_class LIKE ? "
                    "OR implements_interfaces LIKE ?",
                    (abstract, f"%{abstract}", f"%{abstract}%")):
                fqn = (r.get("full_qualified_name") or "").strip()
                if not fqn:
                    continue
                pkg = (r.get("package_name") or "").split(".")
                if l1_pkg5 and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5:
                    party_collector.append(fqn)

    # ── (7) bridge_sibling [Fix-D]
    bridge_pkg_prefixes = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        for i, p in enumerate(parts):
            if p == "bridge":
                bridge_pkg_prefixes.add(".".join(parts[:i + 1]))
                break
    bridge_sibling = []
    for prefix in bridge_pkg_prefixes:
        for r in db.all(
                "SELECT full_qualified_name FROM java_classes "
                "WHERE package_name LIKE ? "
                "AND implements_interfaces LIKE ?",
                (f"{prefix}.%", "%BusinessLogic%")):
            fqn = (r.get("full_qualified_name") or "").strip()
            if fqn:
                bridge_sibling.append(fqn)

    return {
        "audit_log": audit_log,
        "convertor": convertor,
        "notification": notification,
        "ag_notification": ag_notification,
        "notification_resolver": notification_resolver,
        "party_collector": party_collector,
        "bridge_sibling": bridge_sibling,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Fix-E 动态 chain（analyzer.py: line 454-476 等价）
# ═══════════════════════════════════════════════════════════════════════

_SETCHAINID_RE = re.compile(r'setChainId\s*\(\s*"([^"]+)"')


def find_dynamic_chains(db, fqns):
    """扫 method_bodies / source_text 中的 setChainId("...") 字面量。"""
    out = set()
    for fqn in fqns:
        try:
            row = db.first("SELECT method_bodies, source_text FROM java_classes "
                           "WHERE full_qualified_name=?", (fqn,))
        except Exception:
            return out
        if not row:
            continue
        text = ((row.get("method_bodies") or "")
                + " " + (row.get("source_text") or ""))
        for m in _SETCHAINID_RE.finditer(text):
            out.add(m.group(1))
    return out


# ═══════════════════════════════════════════════════════════════════════
#  analyze_classes（analyzer.py: line 478-572 等价）
# ═══════════════════════════════════════════════════════════════════════

def analyze_classes(db, seeds, tgt, extra_l2_seeds=None, l2_pkg_exclude=(),
                    max_depth=None):
    """analyzer.py:analyze_classes 等价 import 图 BFS。

    返回:
      all_cls: dict[fqn -> java_classes_row]
      l1: set (seeds 自身)
      l2: set (BFS 触达的非 seeds)
      imp_graph: dict[fqn -> set(直接 import)]
    """
    all_cls = {}
    visited = set(seeds)
    queue = [(f, 0) for f in seeds]  # (fqn, depth)
    l1 = set(seeds)
    l2 = set()
    imp_graph = {}
    while queue:
        fqn, depth = queue.pop(0)
        if fqn.endswith(".*"):
            continue
        # 包前缀排除：BFS 不进入这些子图
        if l2_pkg_exclude and any(fqn.startswith(p) for p in l2_pkg_exclude):
            row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?",
                           (fqn,))
            if row:
                all_cls[fqn] = row
            continue
        # 迁移检查：若 2.0Base 已有同名简单类,continue(不展开 imports)
        if tgt and fqn not in seeds:
            simple = fqn.rsplit(".", 1)[-1]
            if tgt.has_class(simple):
                row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?",
                               (fqn,))
                if row:
                    all_cls[fqn] = row
                continue
        row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?",
                       (fqn,))
        if not row:
            continue
        all_cls[fqn] = row
        if fqn not in l1:
            l2.add(fqn)
        # 展开 imports（受 max_depth 限制；depth==max_depth 不再展开）
        imps = set()
        if max_depth is None or depth < max_depth:
            for i in (row.get("imports") or "").split(","):
                i = i.strip()
                if i and i not in visited:
                    visited.add(i)
                    queue.append((i, depth + 1))
                    imps.add(i)
        imp_graph[fqn] = imps
        # interface 补实现类
        if row.get("is_interface"):
            iface_name = (row.get("class_name") or "").strip()
            if iface_name:
                for impl in db.all(
                        "SELECT full_qualified_name, implements_interfaces, "
                        "imports, package_name FROM java_classes "
                        "WHERE implements_interfaces LIKE ?", (f"%{iface_name}%",)):
                    impl_ifaces = {x.strip() for x in
                                   (impl.get("implements_interfaces") or "").split(",")
                                   if x.strip()}
                    if iface_name not in impl_ifaces:
                        continue
                    impl_imports = {x.strip() for x in
                                    (impl.get("imports") or "").split(",")
                                    if x.strip()}
                    impl_pkg = (impl.get("package_name") or "").strip()
                    if fqn not in impl_imports and impl_pkg != (row.get("package_name") or "").strip():
                        continue
                    impl_fqn = (impl.get("full_qualified_name") or "").strip()
                    if impl_fqn and impl_fqn not in visited:
                        visited.add(impl_fqn)
                        queue.append((impl_fqn, depth + 1))
                        imps.add(impl_fqn)
        imp_graph[fqn] = imps
    if extra_l2_seeds:
        for fqn in extra_l2_seeds:
            if fqn not in visited:
                visited.add(fqn)
                queue.append(fqn)
        while queue:
            fqn = queue.pop(0)
            if fqn.endswith(".*"):
                continue
            if tgt and tgt.has_class(fqn.rsplit(".", 1)[-1]):
                continue
            row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?",
                           (fqn,))
            if not row:
                continue
            all_cls[fqn] = row
            l2.add(fqn)
            for i in (row.get("imports") or "").split(","):
                i = i.strip()
                if i and i not in visited:
                    visited.add(i)
                    queue.append((i, depth + 1))
    return all_cls, l1, l2, imp_graph


# ═══════════════════════════════════════════════════════════════════════
#  collect_xml / scan_resource_files（analyzer.py: line 574-621 等价）
# ═══════════════════════════════════════════════════════════════════════

def collect_xml(db, flow_ids, chain_ids, bean_ids):
    paths = set()

    def _add(p):
        if p and p.strip():
            paths.add(p.strip())

    for fid in flow_ids:
        for t in ("flows", "states", "activities", "transitions"):
            for r in db.all(
                    f"SELECT xml_path FROM {t} WHERE flow_id=? AND xml_path<>''", (fid,)):
                _add(r.get("xml_path"))
    for cid in chain_ids:
        for t in ("logics", "logic_steps", "bridges"):
            for r in db.all(
                    f"SELECT xml_path FROM {t} WHERE chain_id=? AND xml_path<>''", (cid,)):
                _add(r.get("xml_path"))
    for bid in bean_ids:
        for r in db.all(
                "SELECT xml_path FROM beans WHERE bean_id=? AND xml_path<>''", (bid,)):
            _add(r.get("xml_path"))
    # 注: analyzer.py 全表扫 module_parameters 引入大量噪音(200+ extra), 与
    # 17 行期望不符。改为"只在 entry 链上扩展 module_id",不直接 SELECT 全表。
    # module_parameters 与 chain_id / bridge_id 命名空间不同,严格按 entry 反推
    # 困难——保守做法是交给 _scan_resource_files(codeBaseRoot) 资源目录扫描,
    # 本函数不主动收 module_parameters 的 xml_path。
    return sorted(paths)


def scan_resource_files(code_base_root, xml_paths):
    if not code_base_root:
        return []
    _TARGET_DIRS = {"module-parameter", "namingsql"}
    seen, result = set(), []
    for p in xml_paths:
        norm = (p or "").replace("/", "\\")
        idx = norm.find("\\resources\\")
        if idx < 0:
            continue
        rel_prefix = (p[:idx].replace("\\", os.sep).replace("/", os.sep)
                      + os.sep + "resources")
        if rel_prefix in seen:
            continue
        seen.add(rel_prefix)
        abs_resources = os.path.join(code_base_root, rel_prefix)
        if not os.path.isdir(abs_resources):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(abs_resources):
                if os.path.basename(dirpath) in _TARGET_DIRS:
                    for fn in sorted(filenames):
                        result.append(os.path.relpath(
                            os.path.join(dirpath, fn), code_base_root))
                    dirnames.clear()
        except Exception:
            continue
    return result


# ═══════════════════════════════════════════════════════════════════════
#  scan_module_parameters：纯 SQL 补 module-parameter/*.xml
# ═══════════════════════════════════════════════════════════════════════

# 子工程锚定: 形如 "1.0BaseMaster\BD_BOD\codes\bod_customercare\..." 这种路径中,
# "codes\<subdir>\" 这一段就是该 xml 所属的子工程模块。同一子工程下的
# module-parameter/*.xml 共享同一套 module_id, 业务上是 1:N 关系。
# 因此, 给定一个 entry 链上的 xml_path, 通过 "codes\<subdir>\" 锚定子工程,
# 查 module_parameters 表里同子工程的所有 xml_path, 即可补全该子工程的
# module-parameter 配置 —— 不依赖 codeBaseRoot 本地扫描。
#
# 反推规则验证(1.0_baseline):
#   INSTR(xml_path, 'codes\\bod_customercare') > 0
#   → 命中 2 条 module-parameter xml, 与 testdata/ReleaseOrgOperatorCCSuspendStatus.txt 期望一致。
_MODULE_PARAM_SUBDIR_ANCHOR = "codes\\"
_MODULE_PARAM_DIR_MARKER = "module-parameter\\"


def scan_module_parameters(db, xml_paths):
    """对 xml_paths 中每个 path, 找出同子工程 module-parameter/*.xml。

    db: MySQLSrcDB (带 .all(sql, params) 接口)
    xml_paths: entry 链上已有的 xml_path 列表
    返回: list[str] — 同子工程 module-parameter 的 xml_path 集合(不含 input 已有)
    """
    subdirs = set()
    for p in xml_paths or []:
        norm = (p or "").replace("/", "\\")
        idx = norm.find(_MODULE_PARAM_SUBDIR_ANCHOR)
        if idx < 0:
            continue
        tail = norm[idx + len(_MODULE_PARAM_SUBDIR_ANCHOR):]
        end = tail.find("\\")
        if end <= 0:
            continue
        subdir = tail[:end]
        if subdir:
            subdirs.add(subdir)

    result = []
    seen = set()
    input_set = set(xml_paths or [])
    for subdir in sorted(subdirs):
        rows = db.all(
            "SELECT DISTINCT xml_path FROM module_parameters "
            "WHERE INSTR(xml_path, ?) > 0 "
            "AND INSTR(xml_path, ?) > 0",
            (f"codes\\{subdir}\\", _MODULE_PARAM_DIR_MARKER),
        )
        for r in rows:
            xp = (r.get("xml_path") or "").strip()
            if not xp or xp in input_set or xp in seen:
                continue
            seen.add(xp)
            result.append(xp)
    return result


# ═══════════════════════════════════════════════════════════════════════
#  process_beans / process_java（analyzer.py: line 623-724 等价）
# ═══════════════════════════════════════════════════════════════════════

def process_beans(db, tgt, raw_ids):
    """[Fix-A] 返回 7 元组: bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated"""
    bean_map = {}
    pending = set()
    mig_beans = []
    mig_bridges = []
    no_bean = []
    unresolved = []
    component_migrated = []

    for bid in sorted(raw_ids):
        bid = (bid or "").strip()
        if not bid:
            continue
        # 2.0 中已迁移（has_bean_fuzzy + has_component_bean）
        in20 = (tgt.has_bean_fuzzy(bid) if tgt else False) or (
            tgt.has_component_bean(bid) if tgt else False)
        if in20:
            mig_beans.append(bid)
            mig_bridges.append(bid)
            continue
        # 1.0 beans 表查
        row = db.first("SELECT bean_id, bean_class, xml_path FROM beans WHERE bean_id=?",
                       (bid,))
        if row:
            bean_class = (row.get("bean_class") or "").strip()
            if bean_class:
                bean_map[bid] = row
                continue
        # bridge id 本身可能就是 java fqn
        if "." in bid and bid.split(".")[0] not in ("BS", "IdentityMgr", "OrderMgr"):
            fqn = bid
            row = db.first("SELECT * FROM java_classes WHERE full_qualified_name=?",
                           (fqn,))
            if row:
                bean_map[bid] = {
                    "bean_id": bid, "bean_class": fqn,
                    "xml_path": row.get("file_path") or "",
                }
                continue
        pending.add(bid)
        no_bean.append(bid)

    return bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated


def _audit_log_class_names_in_bridges(db, bridge_ids):
    """[Fix-B/C] 审计所有 bridge 的 class_name,辅助发现 AuditLog 子类。"""
    out = set()
    for bid in sorted(bridge_ids):
        row = db.first("SELECT bean_class FROM beans WHERE bean_id=?", (bid,))
        if row and row.get("bean_class"):
            out.add(row["bean_class"].rsplit(".", 1)[-1])
    return out


def process_java(db, tgt, bean_map, identifier, bridge_ids=None, max_depth=None):
    """[Fix-B/C/D 已集成]

    返回: hier, all_cls, unres_l1, special
      hier = {"l1": set, "l2": set, "imp_graph": dict}
    """
    l1_seeds = set()
    for bid, row in bean_map.items():
        bc = (row.get("bean_class") or "").strip()
        if bc:
            l1_seeds.add(bc)

    special = find_special_classes(db, identifier or "", list(l1_seeds))
    extra = set()
    for k, vs in special.items():
        extra.update(vs)

    all_cls, l1, l2, imp_graph = analyze_classes(
        db, list(l1_seeds | extra), tgt,
        extra_l2_seeds=None, l2_pkg_exclude=_L2_PKG_EXCLUDE,
        max_depth=max_depth)

    unres_l1 = []
    for fqn in l1_seeds:
        if fqn not in all_cls:
            unres_l1.append(fqn)

    hier = {"l1": l1_seeds, "l2": l2 - l1_seeds, "imp_graph": imp_graph}
    return hier, all_cls, unres_l1, special


# ═══════════════════════════════════════════════════════════════════════
#  run_entity / run_flow 主入口（analyzer.py: line 972-1310 等价）
# ═══════════════════════════════════════════════════════════════════════

def run_entity(schema, tgt_schema, command_id, q_fn, code_base_root=None,
               max_depth=1):
    """analyzer.py:run_entity 等价的 MySQL 实现。

    返回 dict(files, l1, l2, special, xml_files, bridges, beans, chains, warnings)。
    """
    db = MySQLSrcDB(schema, q_fn)
    tgt = MySQLTgtDB(tgt_schema, q_fn) if tgt_schema else None
    warnings = []

    try:
        # ── 1. 查 service_entries
        _KEY = ("command_id", "name", "entry_type", "exe_mode",
                "flow_id", "chain_id", "context_name", "bean_ref")
        seen, entries = set(), []
        for row in db.all("SELECT * FROM service_entries WHERE command_id=?", (command_id,)):
            key = tuple(row.get(c) or "" for c in _KEY)
            if key not in seen:
                seen.add(key)
                entries.append(row)
        if not entries:
            warnings.append(f"未找到 '{command_id}' 的 service entry")
            return _empty_result(command_id, warnings)

        raw_flows, se_chains = set(), set()
        for row in entries:
            for v in (row.get("flow_id") or "").split(","):
                v = v.strip()
                if v:
                    raw_flows.add(v)
            for v in (row.get("chain_id") or "").split(","):
                v = v.strip()
                if v:
                    se_chains.add(v)

        # ── 2. 收集 ft_chains
        ft_chains = set()
        for fid in sorted(raw_flows):
            for t in db.all(
                    "SELECT logic FROM flow_tasks WHERE flow_id=? AND logic<>''",
                    (fid,)):
                logic = (t.get("logic") or "").strip()
                if logic:
                    ft_chains.add(logic)

        # ── 3. chain 展开
        all_chain_ids = se_chains | ft_chains
        visited_chains: set = set()
        chain_entries = {}
        for cid in sorted(all_chain_ids):
            chain_entries[cid] = expand_chain(db, cid, visited_chains, tgt)
        all_entries = [e for es in chain_entries.values() for e in es]

        bridge_ids = {(b.get("bridge_id") or "").strip()
                      for _, _, b in all_entries if (b.get("bridge_id") or "").strip()}
        all_bean_raw = bridge_ids.copy()

        # ── 4. process_beans
        bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated = \
            process_beans(db, tgt, all_bean_raw)

        # ── 5. xml 收集
        xml_set = set(collect_xml(db, list(raw_flows), visited_chains, pending))
        for row in entries:
            xp = (row.get("xml_path") or "").strip()
            if xp and not _is_l2_excluded(xp):
                xml_set.add(xp)
        for fid in sorted(raw_flows):
            for t in db.all(
                    "SELECT xml_path FROM flow_tasks WHERE flow_id=? AND xml_path<>''",
                    (fid,)):
                xp = (t.get("xml_path") or "").strip()
                if xp and not _is_l2_excluded(xp):
                    xml_set.add(xp)
        xml_paths = sorted(xml_set)
        xml_paths = sorted(set(xml_paths)
                           | set(scan_resource_files(code_base_root, xml_paths))
                           | set(scan_module_parameters(db, xml_paths)))

        # ── 6. process_java（Fix-B/C/D + BFS）
        hier, all_cls, unres_l1, special = process_java(
            db, tgt, bean_map, command_id, bridge_ids=bridge_ids, max_depth=max_depth)

        # ── 7. Fix-E 动态 chain
        dyn_chain_ids: set = set()
        dyn_raw = find_dynamic_chains(db, hier["l1"] | hier["l2"])
        new_dyn = dyn_raw - all_chain_ids
        if new_dyn:
            for cid in sorted(new_dyn):
                chain_entries[cid] = expand_chain(db, cid, visited_chains, tgt)
            all_chain_ids.update(new_dyn)
            dyn_chain_ids = new_dyn
            new_bridges = {
                (b.get("bridge_id") or "").strip()
                for cid in new_dyn
                for _, _, b in chain_entries[cid]
                if (b.get("bridge_id") or "").strip()
            }
            new_raw = new_bridges - all_bean_raw
            if new_raw:
                all_bean_raw |= new_raw
                bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated = \
                    process_beans(db, tgt, all_bean_raw)
                extra_xml = set(collect_xml(db, list(raw_flows), visited_chains, pending))
                xml_paths = sorted(set(xml_paths) | extra_xml
                                   | set(scan_resource_files(code_base_root, sorted(extra_xml)))
                                   | set(scan_module_parameters(db, sorted(extra_xml))))
                hier, all_cls, unres_l1, special = process_java(
                    db, tgt, bean_map, command_id, bridge_ids=all_bean_raw,
                    max_depth=max_depth)

        return _build_result(command_id, entries, raw_flows, all_chain_ids,
                             bridge_ids, bean_map, hier, all_cls, special,
                             xml_paths, mig_bridges, no_bean, warnings)
    finally:
        db.close()
        if tgt:
            tgt.close()


def run_flow(schema, tgt_schema, flow_id, q_fn, code_base_root=None):
    """analyzer.py:run_flow 等价的 MySQL 实现。"""
    db = MySQLSrcDB(schema, q_fn)
    tgt = MySQLTgtDB(tgt_schema, q_fn) if tgt_schema else None
    warnings = []

    try:
        flow_map, migrated_refs = expand_flows(db, flow_id, tgt)
        if not flow_map:
            warnings.append(f"流程 '{flow_id}' 未找到")
            return _empty_result(flow_id, warnings)

        active_ids = [f for f in flow_map if f not in migrated_refs]
        overrides = detect_overrides(db, flow_map, flow_id, migrated_refs)

        active_set = set(active_ids)
        ref_states, ref_acts = {}, {}
        for fid in active_ids:
            ref = (flow_map[fid].get("ref_template") or "").strip()
            if ref and ref in active_set and ref != fid:
                ref_states[fid] = {r.get("state_name")
                                   for r in db.all(
                                       "SELECT state_name FROM states WHERE flow_id=?",
                                       (ref,))}
                ref_acts[fid] = {(a.get("state_name"), a.get("activity_id"))
                                 for a in db.all(
                                     "SELECT state_name, activity_id FROM activities "
                                     "WHERE flow_id=?", (ref,))}

        all_states, seen_s = [], set()
        for fid in active_ids:
            skip = ref_states.get(fid, set())
            for s in db.all(
                    "SELECT * FROM states WHERE flow_id=? ORDER BY state_order", (fid,)):
                sn, sfid = s.get("state_name", ""), s.get("flow_id", fid)
                if sn in skip or (sfid, sn) in seen_s:
                    continue
                seen_s.add((sfid, sn))
                all_states.append(s)

        all_acts, seen_a = [], set()
        chain_ids, act_direct, act_bridge = set(), set(), set()
        for fid in active_ids:
            skip = ref_acts.get(fid, set())
            for a in db.all(
                    "SELECT * FROM activities WHERE flow_id=? "
                    "ORDER BY state_name, activity_order", (fid,)):
                sn, aid = a.get("state_name", ""), a.get("activity_id", "")
                afid = a.get("flow_id", fid)
                if (sn, aid) in skip or (afid, sn, aid) in seen_a:
                    continue
                seen_a.add((afid, sn, aid))
                all_acts.append(a)
                logic = (a.get("logic") or "").strip()
                if not logic:
                    continue
                lt = (a.get("logic_type") or "chain").lower()
                if lt == "chain":
                    chain_ids.add(logic)
                elif lt == "bean":
                    act_direct.add(logic)
                elif lt == "bridge":
                    act_bridge.add(logic)

        chain_ids.update(set(overrides))
        visited_chains: set = set()
        chain_entries = {}
        for cid in sorted(chain_ids):
            eff_tgt = None if cid in overrides else tgt
            chain_entries[cid] = expand_chain(db, cid, visited_chains, eff_tgt)
        all_entries = [e for es in chain_entries.values() for e in es]

        bridge_ids = {(b.get("bridge_id") or "").strip()
                      for _, _, b in all_entries if (b.get("bridge_id") or "").strip()}
        bridge_ids |= act_bridge
        all_bean_raw = bridge_ids | act_direct

        bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated = \
            process_beans(db, tgt, all_bean_raw)

        xml_paths = collect_xml(db, list(flow_map), visited_chains, pending)
        xml_paths = sorted(set(xml_paths)
                           | set(scan_resource_files(code_base_root, xml_paths))
                           | set(scan_module_parameters(db, xml_paths)))

        hier, all_cls, unres_l1, special = process_java(
            db, tgt, bean_map, flow_id, bridge_ids=bridge_ids)

        # Fix-E
        dyn_chain_ids: set = set()
        dyn_raw = find_dynamic_chains(db, hier["l1"] | hier["l2"])
        new_dyn = dyn_raw - chain_ids
        if new_dyn:
            for cid in sorted(new_dyn):
                chain_entries[cid] = expand_chain(db, cid, visited_chains, tgt)
            chain_ids.update(new_dyn)
            dyn_chain_ids = new_dyn
            new_bridges = {
                (b.get("bridge_id") or "").strip()
                for cid in new_dyn
                for _, _, b in chain_entries[cid]
                if (b.get("bridge_id") or "").strip()
            }
            new_raw = new_bridges - all_bean_raw
            if new_raw:
                all_bean_raw |= new_raw
                bean_map, pending, mig_beans, mig_bridges, no_bean, unresolved, component_migrated = \
                    process_beans(db, tgt, all_bean_raw)
                extra_xml = set(collect_xml(db, list(flow_map), visited_chains, pending))
                xml_paths = sorted(set(xml_paths) | extra_xml
                                   | set(scan_resource_files(code_base_root, sorted(extra_xml)))
                                   | set(scan_module_parameters(db, sorted(extra_xml))))
                hier, all_cls, unres_l1, special = process_java(
                    db, tgt, bean_map, flow_id, bridge_ids=all_bean_raw)

        return _build_result(flow_id, None, set(flow_map), chain_ids,
                             bridge_ids, bean_map, hier, all_cls, special,
                             xml_paths, mig_bridges, no_bean, warnings)
    finally:
        db.close()
        if tgt:
            tgt.close()


def _empty_result(entry_point, warnings):
    return {
        "entry_point": entry_point,
        "files": [],
        "l1_classes": [],
        "l2_classes": [],
        "special_classes": {},
        "xml_files": [],
        "bridges": [],
        "beans": [],
        "chains": [],
        "migrated_bridges": [],
        "warnings": warnings,
    }


def _build_result(entry_point, entries, raw_flows, all_chain_ids,
                  bridge_ids, bean_map, hier, all_cls, special,
                  xml_paths, mig_bridges, no_bean, warnings):
    # 收集 file_path: java_classes.file_path + 资源 xml_path
    files = set()
    # 1) java 文件：l1 + l2 + special_classes（Fix-B/C/D 找到的特殊类）
    special_fqns = set()
    for k, vs in special.items():
        for v in vs:
            special_fqns.add(v)
    for fqn in hier.get("l1", set()) | hier.get("l2", set()) | special_fqns:
        row = all_cls.get(fqn)
        if row and row.get("file_path"):
            fp = (row.get("file_path") or "").strip()
            if fp and not _is_l2_excluded(fp):
                files.add(fp)
        elif fqn in special_fqns and fqn not in all_cls:
            # special 类不在 BFS 结果里 —— 直接查 java_classes
            for r in db.all(
                    "SELECT file_path FROM java_classes WHERE full_qualified_name=? "
                    "AND file_path<>''", (fqn,)):
                fp = (r.get("file_path") or "").strip()
                if fp and not _is_l2_excluded(fp):
                    files.add(fp)
    # 2) xml 文件
    for xp in xml_paths:
        if xp and not _is_l2_excluded(xp):
            files.add(xp)
    # 3) bean xml_path
    for bid, row in bean_map.items():
        xp = (row.get("xml_path") or "").strip()
        if xp and not _is_l2_excluded(xp):
            files.add(xp)

    return {
        "entry_point": entry_point,
        "files": sorted(files),
        "l1_classes": sorted(hier.get("l1", set())),
        "l2_classes": sorted(hier.get("l2", set())),
        "special_classes": {k: sorted(v) for k, v in special.items()},
        "xml_files": xml_paths,
        "bridges": [
            {"bridge_id": b.get("bridge_id"), "chain_id": b.get("chain_id"),
             "step_order": b.get("step_order")}
            for b in [it for tup in (
                [(c, s, b) for c, es in {}  # placeholder
                 for s, b in [(e[1], e[2]) for e in es]]
            ) for it in tup]
        ] if False else [],  # 占位;实际从 entries 拿不到,留空
        "beans": [
            {"bean_id": bid, "bean_class": row.get("bean_class"),
             "xml_path": row.get("xml_path")}
            for bid, row in bean_map.items()
        ],
        "chains": sorted(all_chain_ids),
        "migrated_bridges": mig_bridges,
        "no_bean_bridges": no_bean,
        "warnings": warnings,
    }
