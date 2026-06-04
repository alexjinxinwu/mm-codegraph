#!/usr/bin/env python3
"""MCP server: 把 MySQL 代码知识图谱暴露给 Claude Code 用于代码分析。"""

# 多个schema代表不同的代码仓（"1_0_baseline",    "1_0_Mobilink",    "1_0_bKash",    "1_0_Kenya",  
#     "2_0_baseline",   "2_0_Mobilink",    "2_0_bKash",    "2_0_Kenya",  ）
#  Schema的表结构都是相同的，表之间的关系如下： 
#  ```mermaid
# erDiagram
#     service_entries {
#         bigint id PK
#         string entry_type
#         string name
#         string uri
#         string interface
#         string bean_ref
#         string method_name
#         string context_name
#         string command_id
#         string business_type
#         string request_class
#         string response_class
#         string exe_mode
#         string chain_id
#         string flow_id
#         string is_rec_order
#         string is_check_concurrent
#         string enable_idempotent
#         string context_initializer
#         string listeners
#         string xml_path
#     }
#     flows {
#         bigint id PK
#         string flow_type
#         string flow_id
#         string real_flow_id
#         string template_name
#         string description
#         string ref_template
#         string entry_point
#         string version
#         string plan
#         string xml_path
#     }
#     logics {
#         bigint id PK
#         string chain_id
#         string context_id
#         string xml_path
#     }
#     beans {
#         bigint id PK
#         string bean_id
#         string bean_class
#         string declaration_type
#         string scope
#         string parent_bean
#         string factory_method
#         string init_method
#         string xml_path
#         string java_path
#     }
#     states {
#         bigint id PK
#         string flow_id
#         string state_name
#         bigint state_order
#         string xml_path
#     }
#     flow_tasks {
#         bigint id PK
#         string flow_id
#         string task_type
#         string logic
#         bigint task_order
#         string xml_path
#     }
#     activities {
#         bigint id PK
#         string flow_id
#         string state_name
#         string activity_id
#         string activity_name
#         string logic
#         string logic_type
#         bigint activity_order
#         bigint is_inherited
#         bigint is_overridden
#         string original_logic
#         string xml_path
#     }
#     transitions {
#         bigint id PK
#         string flow_id
#         string state_name
#         string activity_id
#         string method
#         string trans_type
#         string next_target
#         string criteria_operator
#         string criteria_value
#         string xml_path
#     }
#     logic_steps {
#         bigint id PK
#         string chain_id
#         string logic_type
#         bigint step_order
#         string xml_path
#     }
#     bridges {
#         bigint id PK
#         string chain_id
#         string logic_type
#         string bridge_id
#         bigint is_skip
#         bigint is_suspend
#         string before_beans
#         bigint step_order
#         bigint bridge_order
#         string xml_path
#     }
#     java_classes {
#         bigint id PK
#         string class_name
#         string package_name
#         string full_qualified_name
#         string file_path
#         string extends_class
#         string implements_interfaces
#         string annotations
#         bigint is_interface
#         bigint is_abstract
#         bigint is_enum
#         string super_class_fqn
#         string imports
#         string semantic
#     }
#     interceptors {
#         bigint id PK
#         string context_name
#         string stack_name
#         string bean_ref
#         bigint interceptor_order
#         string xml_path
#     }
#     java_methods {
#         bigint id PK
#         string class_fqn
#         string method_name
#         string return_type
#         string parameters
#         string full_signature
#         string modifiers
#         string annotations
#         bigint is_constructor
#         string file_path
#     }
#     module_parameters {
#         bigint id PK
#         string module_id
#         string parameter_name
#         string param_key
#         string param_value
#         string xml_path
#     }
#     service_entries ||--o{ flows : "flow_id -> flow_id"
#     service_entries ||--o{ logics : "chain_id -> chain_id"
#     service_entries ||--o{ beans : "bean_ref -> bean_id"
#     flows ||--o{ states : "flow_id -> flow_id"
#     flows ||--o{ flow_tasks : "flow_id -> flow_id"
#     flows ||--o{ activities : "flow_id -> flow_id"
#     flows ||--o{ transitions : "flow_id -> flow_id"
#     states ||--o{ activities : "flow_id+state_name -> flow_id+state_name"
#     states ||--o{ transitions : "flow_id+state_name -> flow_id+state_name"
#     activities ||--o{ transitions : "activity_id -> activity_id"
#     logics ||--o{ activities : "chain_id <- logic (逻辑关联)"
#     logics ||--o{ flow_tasks : "chain_id <- logic (逻辑关联)"
#     logics ||--o{ logic_steps : "chain_id -> chain_id"
#     logics ||--o{ bridges : "chain_id -> chain_id"
#     logic_steps ||--o{ bridges : "chain_id -> chain_id"
#     bridges ||--|| java_classes : "before_beans -> full_qualified_name"
#     beans ||--|| java_classes : "bean_class -> full_qualified_name"
#     beans ||--o{ interceptors : "bean_id -> bean_ref"
#     java_classes ||--o{ java_methods : "full_qualified_name -> class_fqn"
#  ```

import os
import re
import json
import sys
from collections import defaultdict

import pymysql
from dbutils.pooled_db import PooledDB
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mm-codegraph")

_POOL = None
SCHEMA_RE = re.compile(r"^[A-Za-z0-9_.]+$")
DEFAULT_LIMIT = 200
ALL_TABLES = [
    "activities", "beans", "bridges", "flow_tasks", "flows", "interceptors",
    "java_classes", "java_methods", "logic_steps", "logics",
    "module_parameters", "service_entries", "states", "transitions",
]


def get_pool():
    global _POOL
    if _POOL is None:
        _POOL = PooledDB(
            creator=pymysql,
            maxconnections=int(os.environ.get("MYSQL_POOL_SIZE", "5")),
            host=os.environ.get("MYSQL_HOST", "localhost"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", "root"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            ping=1,
        )
    return _POOL


def _schema(s: str) -> str:
    if not s or not SCHEMA_RE.match(s):
        raise ValueError(f"非法 schema 名: {s!r}（只允许字母、数字、下划线、点）")
    return s


def q(schema: str, sql: str, params=()):
    """在指定 schema 执行查询并返回字典列表。"""
    schema = _schema(schema)
    conn = get_pool().connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"USE `{schema}`")
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def out(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


# ---------- 导航类 ----------

@mcp.tool()
def list_schemas() -> str:
    """列出实例上所有代码知识图谱 schema（每个 schema = 一个代码库/代码组织）。"""
    conn = get_pool().connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            dbs = [r["Database"] for r in cur.fetchall()]
    finally:
        conn.close()
    system = {"information_schema", "mysql", "performance_schema", "sys"}
    return out([d for d in dbs if d not in system])


@mcp.tool()
def schema_overview(schema: str) -> str:
    """返回某 schema 中各表的行数统计，快速了解代码库规模。"""
    result = {}
    for t in ALL_TABLES:
        try:
            result[t] = q(schema, f"SELECT COUNT(*) AS c FROM `{t}`")[0]["c"]
        except Exception as e:
            result[t] = f"error: {e}"
    return out(result)


@mcp.tool()
def search(schema: str, keyword: str, limit: int = 20) -> str:
    """跨核心表关键字搜索（service_entries/flows/beans/java_classes）。
    不确定从哪入手时用它先定位。"""
    like = f"%{keyword}%"
    return out({
        "service_entries": q(schema,
            "SELECT name, entry_type, flow_id, chain_id, bean_ref FROM service_entries "
            "WHERE name LIKE %s OR command_id LIKE %s OR uri LIKE %s LIMIT %s",
            (like, like, like, limit)),
        "flows": q(schema,
            "SELECT flow_id, flow_type, description FROM flows "
            "WHERE flow_id LIKE %s OR description LIKE %s LIMIT %s",
            (like, like, limit)),
        "beans": q(schema,
            "SELECT bean_id, bean_class FROM beans "
            "WHERE bean_id LIKE %s OR bean_class LIKE %s LIMIT %s",
            (like, like, limit)),
        "java_classes": q(schema,
            "SELECT class_name, full_qualified_name FROM java_classes "
            "WHERE class_name LIKE %s OR full_qualified_name LIKE %s LIMIT %s",
            (like, like, limit)),
    })


# ---------- 入口 / 流程 / 状态机 ----------

@mcp.tool()
def find_service_entry(schema: str, keyword: str = "", limit: int = 50) -> str:
    """按 name/uri/command_id/business_type 模糊查找服务入口。keyword 为空则列前 N 条。"""
    if keyword:
        like = f"%{keyword}%"
        rows = q(schema,
            "SELECT * FROM service_entries WHERE name LIKE %s OR uri LIKE %s "
            "OR command_id LIKE %s OR business_type LIKE %s LIMIT %s",
            (like, like, like, like, limit))
    else:
        rows = q(schema, "SELECT * FROM service_entries LIMIT %s", (limit,))
    return out(rows)


@mcp.tool()
def get_service_entry(schema: str, name: str) -> str:
    """获取服务入口详情，并自动解析其关联的 flow、logic chain、bean。"""
    entries = q(schema, "SELECT * FROM service_entries WHERE name = %s", (name,))
    linked = {}
    for e in entries:
        link = {}
        if e.get("flow_id"):
            link["flow"] = q(schema, "SELECT * FROM flows WHERE flow_id=%s", (e["flow_id"],))
        if e.get("chain_id"):
            link["logic"] = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (e["chain_id"],))
        if e.get("bean_ref"):
            link["bean"] = q(schema, "SELECT * FROM beans WHERE bean_id=%s", (e["bean_ref"],))
        linked[e["name"]] = link
    return out({"service_entries": entries, "linked": linked})


@mcp.tool()
def get_flow(schema: str, flow_id: str) -> str:
    """获取流程基本信息 + states 列表 + flow_tasks。"""
    return out({
        "flow": q(schema, "SELECT * FROM flows WHERE flow_id=%s", (flow_id,)),
        "states": q(schema,
            "SELECT * FROM states WHERE flow_id=%s ORDER BY state_order", (flow_id,)),
        "flow_tasks": q(schema,
            "SELECT * FROM flow_tasks WHERE flow_id=%s ORDER BY task_order", (flow_id,)),
    })


@mcp.tool()
def get_state(schema: str, flow_id: str, state_name: str) -> str:
    """获取某状态下的 activities（含 logic）与 transitions（状态流转）。"""
    return out({
        "activities": q(schema,
            "SELECT * FROM activities WHERE flow_id=%s AND state_name=%s ORDER BY activity_order",
            (flow_id, state_name)),
        "transitions": q(schema,
            "SELECT * FROM transitions WHERE flow_id=%s AND state_name=%s",
            (flow_id, state_name)),
    })


@mcp.tool()
def get_flow_statemachine(schema: str, flow_id: str) -> str:
    """构建整个流程的状态机视图：所有 state 及其 activities、transitions（含转移目标与判定条件）。"""
    states = q(schema, "SELECT * FROM states WHERE flow_id=%s ORDER BY state_order", (flow_id,))
    acts = q(schema,
        "SELECT * FROM activities WHERE flow_id=%s ORDER BY state_name, activity_order", (flow_id,))
    trans = q(schema, "SELECT * FROM transitions WHERE flow_id=%s", (flow_id,))
    a_by, t_by = defaultdict(list), defaultdict(list)
    for a in acts:
        a_by[a["state_name"]].append(a)
    for t in trans:
        t_by[t["state_name"]].append(t)
    sm = [{
        "state": s,
        "activities": a_by.get(s["state_name"], []),
        "transitions": t_by.get(s["state_name"], []),
    } for s in states]
    return out({"flow_id": flow_id, "state_machine": sm})


# ---------- 逻辑链 ----------

@mcp.tool()
def resolve_chain(schema: str, chain_id: str) -> str:
    """解析逻辑链：logics + logic_steps + bridges，并把 bridges.before_beans
    解析到对应的 java_classes（支持逗号分隔的多个 FQN）。"""
    logics = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (chain_id,))
    steps = q(schema,
        "SELECT * FROM logic_steps WHERE chain_id=%s ORDER BY step_order", (chain_id,))
    bridges = q(schema,
        "SELECT * FROM bridges WHERE chain_id=%s ORDER BY step_order, bridge_order", (chain_id,))
    classes = {}
    for b in bridges:
        for fqn in re.split(r"[,;\s]+", (b.get("before_beans") or "").strip()):
            if fqn and fqn not in classes:
                jc = q(schema,
                    "SELECT class_name, full_qualified_name, file_path, semantic "
                    "FROM java_classes WHERE full_qualified_name=%s", (fqn,))
                if jc:
                    classes[fqn] = jc
    return out({"logics": logics, "logic_steps": steps,
                "bridges": bridges, "resolved_classes": classes})


# ---------- Bean / Java ----------

@mcp.tool()
def find_bean(schema: str, keyword: str, limit: int = 50) -> str:
    """按 bean_id 或 bean_class 模糊查找 bean。"""
    like = f"%{keyword}%"
    return out(q(schema,
        "SELECT * FROM beans WHERE bean_id LIKE %s OR bean_class LIKE %s LIMIT %s",
        (like, like, limit)))


@mcp.tool()
def find_class(schema: str, keyword: str, exact: bool = False, limit: int = 50) -> str:
    """查找 Java 类。exact=True 按 full_qualified_name 精确匹配，否则按类名/FQN 模糊匹配。"""
    cols = ("id, class_name, package_name, full_qualified_name, file_path, "
            "is_interface, is_abstract, is_enum, super_class_fqn")
    if exact:
        return out(q(schema,
            f"SELECT {cols} FROM java_classes WHERE full_qualified_name=%s LIMIT %s",
            (keyword, limit)))
    like = f"%{keyword}%"
    return out(q(schema,
        f"SELECT {cols} FROM java_classes "
        "WHERE class_name LIKE %s OR full_qualified_name LIKE %s LIMIT %s",
        (like, like, limit)))


@mcp.tool()
def get_class(schema: str, fqn: str, include_methods: bool = True) -> str:
    """获取类完整信息（含 semantic 语义、注解、继承/实现关系）+ 方法列表
    + 子类/实现类 + 由它声明的 bean。"""
    result = {"class": q(schema, "SELECT * FROM java_classes WHERE full_qualified_name=%s", (fqn,))}
    if include_methods:
        result["methods"] = q(schema,
            "SELECT method_name, return_type, parameters, full_signature, modifiers, "
            "annotations, is_constructor FROM java_methods WHERE class_fqn=%s", (fqn,))
    result["subclasses"] = q(schema,
        "SELECT class_name, full_qualified_name FROM java_classes "
        "WHERE extends_class=%s OR super_class_fqn=%s LIMIT 100", (fqn, fqn))
    result["implementors"] = q(schema,
        "SELECT class_name, full_qualified_name FROM java_classes "
        "WHERE implements_interfaces LIKE %s LIMIT 100", (f"%{fqn}%",))
    result["beans"] = q(schema,
        "SELECT bean_id, scope FROM beans WHERE bean_class=%s", (fqn,))
    return out(result)


@mcp.tool()
def find_method(schema: str, method_name: str = "", class_fqn: str = "", limit: int = 100) -> str:
    """按方法名和/或所属类 FQN 查找 java 方法。"""
    conds, params = [], []
    if method_name:
        conds.append("method_name = %s"); params.append(method_name)
    if class_fqn:
        conds.append("class_fqn = %s"); params.append(class_fqn)
    where = " AND ".join(conds) if conds else "1=1"
    params.append(limit)
    return out(q(schema,
        "SELECT class_fqn, method_name, full_signature, modifiers, annotations "
        f"FROM java_methods WHERE {where} LIMIT %s", tuple(params)))


# ---------- 只读 SQL 兜底 ----------

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|call|load|rename|into|outfile)\b",
    re.I)


@mcp.tool()
def sql_query(schema: str, sql: str, limit: int = 200) -> str:
    """在指定 schema 执行只读查询（上面工具无法覆盖时使用）。仅允许单条 SELECT/WITH。"""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise ValueError("只允许单条语句")
    if not re.match(r"^\s*(select|with)\b", s, re.I):
        raise ValueError("只允许 SELECT/WITH 查询")
    if _FORBIDDEN.search(s):
        raise ValueError("检测到非只读关键字")
    if not re.search(r"\blimit\b", s, re.I):
        s = f"{s} LIMIT {int(limit)}"
    return out(q(schema, s))


# ---------- Service Impact Search ----------

@mcp.tool()
def search_service_impact(
    schema: str,
    commandId: str = None,
    flowId: str = None,
    direction: str = "both",
    maxDepth: int = 20,
    codeBaseRoot: str = None,
) -> str:
    """搜索服务影响范围。基于 13 张表的 ER 关系遍历 + analyzer.py 启发式（Fix-B/C/D
    特殊类 + REF_CHAIN 递归 + import 图 BFS + 动态 chain + 可选资源目录扫描），
    输出受影响文件列表。

    Args:
        schema: 数据库 schema
        commandId: 服务入口 command_id（可选，二选一）
        flowId: 流程 ID（可选，二选一）
        direction: 遍历方向 forward/backward/both
        maxDepth: 最大遍历深度（默认 20）
        codeBaseRoot: 代码库根目录绝对路径（可选）。传入时触发
            resources/{module-parameter, namingsql}/*.xml 扫描，行为与
            analyzer.py:scan_resource_files 等价。
            缺省时自动读环境变量 MM_CODEGRAPH_CODEBASE_ROOT（命中则等效于传参）。

    资源文件覆盖范围：
        - module-parameter/*.xml 由 SQL 阶段（scan_module_parameters）覆盖，
          不依赖 codeBaseRoot。
        - namingsql/*.xml 在 MySQL 中没有索引，只能靠 codeBaseRoot 的
          os.walk 才能扫到。
    """
    # 参数校验
    if not commandId and not flowId:
        raise ValueError("At least one of commandId or flowId must be provided")
    if direction not in ("forward", "backward", "both"):
        raise ValueError("direction must be one of: forward, backward, both")
    if maxDepth <= 0:
        raise ValueError("maxDepth must be a positive integer")
    # 注：direction / maxDepth 仍接受但**当前实现已不使用**。
    # 行为完全由 _explore_phase 决定（沿 analyzer.py:run_entity 的 chain 派生语义）。
    # 这两个参数仅作向后兼容保留，调用方传什么值都得到相同 files 集合。
    if codeBaseRoot is not None and codeBaseRoot != "":
        if not isinstance(codeBaseRoot, str):
            raise ValueError("codeBaseRoot must be a string or None")
        if not os.path.isabs(codeBaseRoot):
            raise ValueError(f"codeBaseRoot must be an absolute path: {codeBaseRoot!r}")
        if not os.path.isdir(codeBaseRoot):
            raise ValueError(f"codeBaseRoot does not exist or is not a directory: {codeBaseRoot!r}")
    # 兜底: codeBaseRoot 未传时, 读环境变量 MM_CODEGRAPH_CODEBASE_ROOT;
    # 目录不存在则忽略(后续 Plan B 会按 None 走并追加 warning)。
    if not codeBaseRoot:
        env_root = os.environ.get("MM_CODEGRAPH_CODEBASE_ROOT", "").strip()
        if env_root and os.path.isdir(env_root):
            codeBaseRoot = env_root
        else:
            # 硬默认值: 本机 MobileMoneyMonorepo 代码根。目录不存在时静默回退,
            # 后续 Plan B/Plan C 自然走不到文件, 仍会写 skipped warning。
            default_root = "D:/2026/MobileMoneyMonorepo"
            if os.path.isdir(default_root):
                codeBaseRoot = default_root

    entry_point = commandId or flowId
    warnings = []

    # ── 先验阶段：REF_CHAIN 递归 + bean 派生 + 特殊类发现 + import 图 BFS
    # ── + 动态 chain —— 把"ER 之外"的文件先收上来，再走现有 _traverse_forward
    pre_files, pre_warnings = _explore_phase(
        schema, entry_point, commandId, flowId, maxDepth, warnings,
    )
    # 合并先验阶段的迁移过滤 warnings（此前被丢弃，导致迁移过滤是否生效不可见）
    warnings.extend(pre_warnings)

    # 查找入口 service_entry 或 flow（保留原行为）
    entry = None
    if commandId:
        entries = q(schema,
            "SELECT * FROM service_entries WHERE command_id=%s LIMIT 1", (commandId,))
        if entries:
            entry = entries[0]
            entry["table"] = "service_entry"
    elif flowId:
        entries = q(schema,
            "SELECT * FROM service_entries WHERE flow_id=%s LIMIT 1", (flowId,))
        if entries:
            entry = entries[0]
            entry["table"] = "service_entry"

    if not entry:
        warnings.append(f"No service entry found for {commandId or flowId}")
        return out({
            "entryPoint": entry_point,
            "direction": direction,
            "totalImpacted": len(pre_files),
            "files": sorted(pre_files),
            "impactChain": [],
            "warnings": warnings,
        })

    # ── Plan A：files 集合由 _explore_phase + _scan_resource_files 提供
    # 显式**不**调用 _traverse_forward / _traverse_backward，因为它们会从
    # entry 沿所有 states / activities / chains 扩散，把整个 flow 上的
    # 全部文件（5011+ 条噪音）收上来。这与 analyzer.py:run_entity 的
    # "按 entry 派生的 chain 链" 语义不符，也与 ReleaseOrgOperatorCCSuspendStatus
    # 的 17 行事实断言不符。

    files = {}  # {path: {"path": path, "type": type}}
    edges = []  # 保留字段语义（向后兼容），但 _explore_phase 不产出 edge 列表

    # ── 合并 _explore_phase 收集的文件（pre_files 是 path 字符串集合）
    for fp in pre_files:
        if fp and fp not in files:
            ftype = "xml" if fp.lower().endswith(".xml") else "java"
            files[fp] = {"path": fp, "type": ftype}

    # ── Plan B：可选资源目录扫描
    if codeBaseRoot:
        try:
            xml_paths_for_walk = [
                v["path"] for v in files.values()
                if v.get("type") == "xml"
            ]
            resource_files = _scan_resource_files(codeBaseRoot, xml_paths_for_walk)
            for fp in resource_files:
                if fp and fp not in files:
                    files[fp] = {"path": fp, "type": "xml"}
        except Exception as e:
            warnings.append(f"Resource directory scan failed at {codeBaseRoot}: {e}")

        # ── Plan C：子工程锚定的 namingsql 收窄
        # Plan B 的 resources/ 全树 walk 会把同 resources 根下其它子工程的
        # namingsql 也卷进来；这里按 entry 链 xml_path 的 'codes\\<subdir>\\'
        # 锚点收窄到本子工程的 namingsql/*.xml。
        try:
            xml_anchors = [v["path"] for v in files.values()
                           if v.get("type") == "xml"]
            sub_roots = _derive_subproject_roots(xml_anchors, codeBaseRoot)
            if sub_roots:
                ns_files = _scan_namingsql_by_subproject(codeBaseRoot, sub_roots)
                for fp in ns_files:
                    if fp and fp not in files:
                        files[fp] = {"path": fp, "type": "xml"}
        except Exception as e:
            warnings.append(f"Subproject-anchored namingsql scan failed: {e}")
    else:
        warnings.append("Resource directory scan skipped: codeBaseRoot not provided")

    result = {
        "entryPoint": entry_point,
        "direction": direction,
        "totalImpacted": len(files),
        "files": sorted([v["path"] for v in files.values()]),
        "impactChain": edges,
        "warnings": warnings,
    }
    return out(result)


def _traverse_forward(schema, node, visited, depth, max_depth, files, edges, warnings):
    """正向 BFS 遍历：service_entry → flow/logic/bean/interceptor"""
    node_key = f"{node.get('table', 'service_entry')}:{node.get('id', node.get('name', ''))}"
    if node_key in visited:
        return
    visited.add(node_key)

    table = node.get("table", "service_entry")

    # 收集文件
    _collect_files(schema, node, files)

    if depth >= max_depth:
        warnings.append(f"Max depth {max_depth} reached at {node_key}")
        return

    if table == "service_entry":
        # 沿 chain_id 遍历 logics
        if node.get("chain_id"):
            logics = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (node["chain_id"],))
            for logic in logics:
                logic["table"] = "logic"
                _add_edge(edges, node_key, f"logic:{logic['chain_id']}")
                _traverse_forward(schema, logic, visited, depth + 1, max_depth, files, edges, warnings)

        # 沿 flow_id 遍历 flows 和 flow_tasks
        _flow_id = node.get("flow_id")
        if _flow_id:
            flows = q(schema, "SELECT * FROM flows WHERE flow_id=%s", (_flow_id,))
            for flow in flows:
                flow["table"] = "flow"
                _add_edge(edges, node_key, f"flow:{flow['flow_id']}")
                _traverse_forward(schema, flow, visited, depth + 1, max_depth, files, edges, warnings)

            # 从 service_entry 直接遍历 flow_tasks（当 flow_id 在 service_entry 中时）
            flow_tasks = q(schema,
                "SELECT * FROM flow_tasks WHERE flow_id=%s ORDER BY task_order", (_flow_id,))
            for task in flow_tasks:
                task["table"] = "flow_task"
                _add_edge(edges, node_key, f"flow_task:{task['task_order']}")
                _traverse_forward(schema, task, visited, depth + 1, max_depth, files, edges, warnings)

        # 沿 bean_ref 遍历 beans
        if node.get("bean_ref"):
            beans = q(schema, "SELECT * FROM beans WHERE bean_id=%s", (node["bean_ref"],))
            for bean in beans:
                bean["table"] = "bean"
                _add_edge(edges, node_key, f"bean:{bean['bean_id']}")
                _traverse_forward(schema, bean, visited, depth + 1, max_depth, files, edges, warnings)

        # 沿 context_name 遍历 interceptors
        if node.get("context_name"):
            interceptors = q(schema,
                "SELECT * FROM interceptors WHERE context_name=%s", (node["context_name"],))
            for intcp in interceptors:
                intcp["table"] = "interceptor"
                _add_edge(edges, node_key, f"interceptor:{intcp['bean_ref']}")
                _traverse_forward(schema, intcp, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "flow":
        # 遍历 states
        flow_id = node.get("flow_id")
        states = q(schema, "SELECT * FROM states WHERE flow_id=%s ORDER BY state_order", (flow_id,))
        for state in states:
            state["table"] = "state"
            _add_edge(edges, node_key, f"state:{state['state_name']}")
            _traverse_forward(schema, state, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 flow_tasks
        flow_tasks = q(schema,
            "SELECT * FROM flow_tasks WHERE flow_id=%s ORDER BY task_order", (flow_id,))
        for task in flow_tasks:
            task["table"] = "flow_task"
            _add_edge(edges, node_key, f"flow_task:{task['task_order']}")
            _traverse_forward(schema, task, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "state":
        # 遍历 activities
        flow_id = node.get("flow_id")
        state_name = node.get("state_name")
        activities = q(schema,
            "SELECT * FROM activities WHERE flow_id=%s AND state_name=%s ORDER BY activity_order",
            (flow_id, state_name))
        for act in activities:
            act["table"] = "activity"
            _add_edge(edges, node_key, f"activity:{act['activity_id']}")
            _traverse_forward(schema, act, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 transitions
        transitions = q(schema,
            "SELECT * FROM transitions WHERE flow_id=%s AND state_name=%s",
            (flow_id, state_name))
        for trans in transitions:
            trans["table"] = "transition"
            _add_edge(edges, node_key, f"transition:{trans['next_target'] or trans['state_name']}")
            # 沿 next_target 递归（同一 flow 内）
            if trans.get("next_target") and trans["next_target"] != state_name:
                next_states = q(schema,
                    "SELECT * FROM states WHERE flow_id=%s AND state_name=%s",
                    (flow_id, trans["next_target"]))
                for ns in next_states:
                    ns["table"] = "state"
                    _traverse_forward(schema, ns, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "activity":
        # 沿 logic 字段遍历 logics
        if node.get("logic"):
            logics = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (node["logic"],))
            for logic in logics:
                logic["table"] = "logic"
                _add_edge(edges, node_key, f"logic:{logic['chain_id']}")
                _traverse_forward(schema, logic, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 transitions（通过 activity_id 关联）
        activity_id = node.get("activity_id")
        if activity_id:
            transitions = q(schema, "SELECT * FROM transitions WHERE activity_id=%s", (activity_id,))
            for trans in transitions:
                trans["table"] = "transition"
                _add_edge(edges, node_key, f"transition:{trans.get('next_target', activity_id)}")
                _traverse_forward(schema, trans, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "flow_task":
        # 沿 logic 字段遍历 logics
        if node.get("logic"):
            logics = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (node["logic"],))
            for logic in logics:
                logic["table"] = "logic"
                _add_edge(edges, node_key, f"logic:{logic['chain_id']}")
                _traverse_forward(schema, logic, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "logic":
        # 遍历 logic_steps
        chain_id = node.get("chain_id")
        steps = q(schema,
            "SELECT * FROM logic_steps WHERE chain_id=%s ORDER BY step_order", (chain_id,))
        for step in steps:
            step["table"] = "logic_step"
            _add_edge(edges, node_key, f"logic_step:{step['step_order']}")
            _traverse_forward(schema, step, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 bridges
        bridges = q(schema,
            "SELECT * FROM bridges WHERE chain_id=%s ORDER BY step_order, bridge_order", (chain_id,))
        for bridge in bridges:
            bridge["table"] = "bridge"
            _add_edge(edges, node_key, f"bridge:{bridge['bridge_id']}")
            _traverse_forward(schema, bridge, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 activities（logic 通过 logic 字段关联）
        activities = q(schema, "SELECT * FROM activities WHERE logic=%s ORDER BY activity_order", (chain_id,))
        for act in activities:
            act["table"] = "activity"
            _add_edge(edges, node_key, f"activity:{act['activity_id']}")
            _traverse_forward(schema, act, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 flow_tasks（logic 通过 logic 字段关联）
        flow_tasks = q(schema, "SELECT * FROM flow_tasks WHERE logic=%s ORDER BY task_order", (chain_id,))
        for task in flow_tasks:
            task["table"] = "flow_task"
            _add_edge(edges, node_key, f"flow_task:{task['task_order']}")
            _traverse_forward(schema, task, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "bridge":
        # 沿 before_beans / after_beans 遍历 beans
        for field in ("before_beans", "after_beans"):
            fqns = (node.get(field) or "").strip()
            if not fqns:
                continue
            for fqn in re.split(r"[,;\s]+", fqns):
                if not fqn:
                    continue
                beans = q(schema, "SELECT * FROM beans WHERE bean_class=%s", (fqn,))
                for bean in beans:
                    bean["table"] = "bean"
                    _add_edge(edges, node_key, f"bean:{bean['bean_id']}")
                    _traverse_forward(schema, bean, visited, depth + 1, max_depth, files, edges, warnings)

        # 遍历 bridges（bridge_id 可能引用另一个 logic chain）
        bridge_id = node.get("bridge_id")
        if bridge_id:
            ref_logics = q(schema, "SELECT * FROM logics WHERE chain_id=%s", (bridge_id,))
            for ref_logic in ref_logics:
                ref_logic["table"] = "logic"
                _add_edge(edges, node_key, f"logic:{ref_logic['chain_id']}")
                _traverse_forward(schema, ref_logic, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "bean":
        # 遍历 interceptors（通过 bean_id → bean_ref 关联）
        bean_id = node.get("bean_id")
        if bean_id:
            interceptors = q(schema, "SELECT * FROM interceptors WHERE bean_ref=%s", (bean_id,))
            for intcp in interceptors:
                intcp["table"] = "interceptor"
                _add_edge(edges, node_key, f"interceptor:{intcp.get('bean_ref', intcp.get('id', ''))}")
                _traverse_forward(schema, intcp, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "java_class":
        # 遍历 java_methods（通过 full_qualified_name → class_fqn 关联）
        fqn = node.get("full_qualified_name")
        if fqn:
            methods = q(schema,
                "SELECT method_name, full_signature FROM java_methods WHERE class_fqn=%s",
                (fqn,))
            for method in methods:
                method["table"] = "java_method"
                _add_edge(edges, node_key, f"java_method:{method.get('method_name', method.get('id', ''))}")


def _traverse_backward(schema, node, visited, depth, max_depth, files, edges, warnings):
    """反向 BFS 遍历：查找谁指向当前节点"""
    node_key = f"{node.get('table', 'service_entry')}:{node.get('id', node.get('name', ''))}_back"
    if node_key in visited:
        return
    visited.add(node_key)

    table = node.get("table", "service_entry")

    # 收集文件
    _collect_files(schema, node, files)

    if depth >= max_depth:
        warnings.append(f"Max depth {max_depth} reached at {node_key}")
        return

    if table == "service_entry" or (table == "service_entry" and node.get("_back_key")):
        # 反向查找：哪些 service_entry 的 flow_id 指向当前 flow
        if node.get("flow_id"):
            upstream = q(schema,
                "SELECT * FROM service_entries WHERE flow_id=%s", (node["flow_id"],))
            for se in upstream:
                se["table"] = "service_entry"
                se["_back_key"] = True
                _add_edge(edges, f"service_entry:{se['name']}_back", f"service_entry:{se.get('name', '')}")
                _traverse_backward(schema, se, visited, depth + 1, max_depth, files, edges, warnings)

        # 反向查找：哪些 service_entry 的 chain_id 指向当前 chain
        if node.get("chain_id"):
            upstream = q(schema,
                "SELECT * FROM service_entries WHERE chain_id=%s", (node["chain_id"],))
            for se in upstream:
                se["table"] = "service_entry"
                se["_back_key"] = True
                _add_edge(edges, f"service_entry:{se['name']}_back", f"service_entry:{se.get('name', '')}")
                _traverse_backward(schema, se, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "flow":
        # 反向查找：哪些 service_entries 使用该 flow_id
        flow_id = node.get("flow_id")
        if flow_id:
            upstream = q(schema,
                "SELECT * FROM service_entries WHERE flow_id=%s", (flow_id,))
            for se in upstream:
                se["table"] = "service_entry"
                se["_back_key"] = True
                _add_edge(edges, f"service_entry:{se.get('name', '')}_back", f"service_entry:{se.get('name', '')}")
                _traverse_backward(schema, se, visited, depth + 1, max_depth, files, edges, warnings)

    elif table == "logic":
        # 反向查找：哪些 service_entries/activities/flow_tasks 使用该 chain_id
        chain_id = node.get("chain_id")
        if chain_id:
            # service_entries
            for se in q(schema, "SELECT * FROM service_entries WHERE chain_id=%s", (chain_id,)):
                se["table"] = "service_entry"
                se["_back_key"] = True
                _add_edge(edges, f"service_entry:{se.get('name', '')}_back", f"service_entry:{se.get('name', '')}")
                _traverse_backward(schema, se, visited, depth + 1, max_depth, files, edges, warnings)
            # activities
            for act in q(schema, "SELECT * FROM activities WHERE logic=%s", (chain_id,)):
                act["table"] = "activity"
                act["_back_key"] = True
                _add_edge(edges, f"activity:{act.get('activity_id', act.get('id', ''))}_back", f"activity:{act.get('activity_id', act.get('id', ''))}")
                _traverse_backward(schema, act, visited, depth + 1, max_depth, files, edges, warnings)
            # flow_tasks
            for task in q(schema, "SELECT * FROM flow_tasks WHERE logic=%s", (chain_id,)):
                task["table"] = "flow_task"
                task["_back_key"] = True
                _add_edge(edges, f"flow_task:{task.get('task_order', task.get('id', ''))}_back", f"flow_task:{task.get('task_order', task.get('id', ''))}")
                _traverse_backward(schema, task, visited, depth + 1, max_depth, files, edges, warnings)

    elif table in ("flow_task", "bridge", "bean", "state", "activity"):
        pass  # 简化：主要通过 service_entry 的 flow_id/chain_id 反向查找


def _collect_files(schema, node, files):
    """收集节点关联的文件路径"""
    # 收集 xml_path（适用于所有表）
    if node.get("xml_path"):
        path = node["xml_path"]
        files[path] = {"path": path, "type": "xml"}

    # 收集 java_path
    table = node.get("table")
    if table == "bean" and node.get("bean_class"):
        # 通过 bean_class 查找 java_class
        jc = q(schema,
            "SELECT file_path FROM java_classes WHERE full_qualified_name=%s LIMIT 1",
            (node["bean_class"],))
        if jc and jc[0].get("file_path"):
            path = jc[0]["file_path"]
            files[path] = {"path": path, "type": "java"}
    elif table == "service_entry" and node.get("bean_ref"):
        beans = q(schema, "SELECT bean_class FROM beans WHERE bean_id=%s", (node["bean_ref"],))
        for bean in beans:
            if bean.get("bean_class"):
                jc = q(schema,
                    "SELECT file_path FROM java_classes WHERE full_qualified_name=%s LIMIT 1",
                    (bean["bean_class"],))
                if jc and jc[0].get("file_path"):
                    path = jc[0]["file_path"]
                    files[path] = {"path": path, "type": "java"}
    elif table == "flow_task" and node.get("logic"):
        # 遍历 flow_task 引用的 logic 的 xml_path
        logics = q(schema, "SELECT xml_path FROM logics WHERE chain_id=%s", (node["logic"],))
        for logic in logics:
            if logic.get("xml_path"):
                files[logic["xml_path"]] = {"path": logic["xml_path"], "type": "xml"}
    elif table == "java_class" and node.get("file_path"):
        # 收集 java_class 的文件路径
        files[node["file_path"]] = {"path": node["file_path"], "type": "java"}


def _add_edge(edges, from_key, to_key):
    """添加边，避免重复"""
    edge = {"from": from_key, "to": to_key}
    if edge not in edges:
        edges.append(edge)


# ---------- Service Impact: analyzer.py 启发式增强（Plan B 完整） ----------

def _expand_chains_recursive(schema, initial_cids, visited):
    """REF_CHAIN 递归展开。BFS 沿 logic_steps.logic_type='REF_CHAIN'
    的 bridges.bridge_id 引用另一 chain_id。visited 集合防环。"""
    queue = list(initial_cids)
    while queue:
        cid = queue.pop(0)
        if cid in visited:
            continue
        visited.add(cid)
        try:
            rows = q(schema,
                "SELECT DISTINCT bridge_id FROM logic_steps "
                "JOIN bridges USING (chain_id, step_order) "
                "WHERE chain_id=%s AND logic_type='REF_CHAIN' AND bridge_id<>''",
                (cid,))
        except Exception:
            continue
        for row in rows:
            ref = (row.get("bridge_id") or "").strip()
            if ref and ref not in visited:
                queue.append(ref)
    return visited


def _collect_l1_fqns_from_beans(schema, bridge_ids):
    """bridge_id 查 beans.bean_class，返回 FQN 集合。"""
    if not bridge_ids:
        return set()
    placeholders = ",".join(["%s"] * len(bridge_ids))
    rows = q(schema,
        f"SELECT DISTINCT bean_class FROM beans "
        f"WHERE bean_id IN ({placeholders}) AND bean_class<>''",
        tuple(bridge_ids))
    return {(r.get("bean_class") or "").strip() for r in rows} - {""}


def _extends_or_implements_in_pkg5(schema, abstract_cls, l1_pkg5, allow_classname_kw=""):
    """按 extends_class / implements_interfaces 查抽象类的实现。
    二次过滤：l1 5 级包前缀命中 OR 类名含 allow_classname_kw。"""
    out = set()
    try:
        candidates = q(schema,
            "SELECT full_qualified_name, package_name, class_name FROM java_classes "
            "WHERE extends_class=%s OR extends_class LIKE %s "
            "OR implements_interfaces LIKE %s",
            (abstract_cls, f"%{abstract_cls}", f"%{abstract_cls}%"))
    except Exception:
        return out
    for r in candidates:
        fqn = (r.get("full_qualified_name") or "").strip()
        if not fqn:
            continue
        pkg = (r.get("package_name") or "").split(".")
        pkg5_match = bool(l1_pkg5) and len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5
        name_match = bool(allow_classname_kw) and allow_classname_kw in (r.get("class_name") or "")
        if pkg5_match or name_match:
            out.add(fqn)
    return out


def _discover_special_classes(schema, identifier, l1_fqns):
    """analyzer.py Fix-B/C/D 启发式：7 类特殊类 + bridge_sibling。
    返回 dict 含每个分类的 FQN 集合与合并的 all 集合。"""
    l1_pkg5 = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        if len(parts) >= 6:
            l1_pkg5.add(".".join(parts[:5]))

    audit_log = set()
    if l1_pkg5:
        for r in q(schema,
            "SELECT full_qualified_name, package_name FROM java_classes "
            "WHERE class_name LIKE %s",
            ("%BuildAuditLog%",)):
            fqn = (r.get("full_qualified_name") or "").strip()
            if not fqn:
                continue
            pkg = (r.get("package_name") or "").split(".")
            if len(pkg) >= 5 and ".".join(pkg[:5]) in l1_pkg5:
                audit_log.add(fqn)

    convertor = set()
    for r in q(schema,
        "SELECT full_qualified_name FROM java_classes "
        "WHERE class_name=%s", (f"{identifier}Convertor",)):
        fqn = (r.get("full_qualified_name") or "").strip()
        if fqn:
            convertor.add(fqn)

    notification = _extends_or_implements_in_pkg5(
        schema, "AbstractIdentityActionNotificationParamCollector", l1_pkg5)
    ag_notification = _extends_or_implements_in_pkg5(
        schema, "AbstractCallBackAGParameterMessageEvent", l1_pkg5,
        allow_classname_kw=identifier)
    notification_resolver = _extends_or_implements_in_pkg5(
        schema, "AbstractNotificationResolverAdaptor", l1_pkg5,
        allow_classname_kw=identifier)

    party_collector = set()
    for abstract in ("ReceiverPartyCollector", "InitiatorParentPartyCollector"):
        party_collector |= _extends_or_implements_in_pkg5(
            schema, abstract, l1_pkg5)

    bridge_sibling = set()
    bridge_pkg_prefixes = set()
    for fqn in l1_fqns:
        parts = fqn.split(".")
        for i, p in enumerate(parts):
            if p == "bridge":
                bridge_pkg_prefixes.add(".".join(parts[:i + 1]))
                break
    for prefix in bridge_pkg_prefixes:
        for r in q(schema,
            "SELECT full_qualified_name FROM java_classes "
            "WHERE package_name LIKE %s "
            "AND implements_interfaces LIKE '%%BusinessLogic%%'",
            (f"{prefix}.%",)):
            fqn = (r.get("full_qualified_name") or "").strip()
            if fqn:
                bridge_sibling.add(fqn)

    all_special = (audit_log | convertor | notification | ag_notification
                   | notification_resolver | party_collector | bridge_sibling)
    return {
        "audit_log": audit_log,
        "convertor": convertor,
        "notification": notification,
        "ag_notification": ag_notification,
        "notification_resolver": notification_resolver,
        "party_collector": party_collector,
        "bridge_sibling": bridge_sibling,
        "all": all_special,
    }


def _derive_migrated_schemas(schema):
    """根据源 schema 推断"已迁移"对照库（2.0）。

    1_0_<site>   → [2_0_<site>, 2_0_baseline]   （site 库优先，baseline 兜底）
    1_0_baseline → [2_0_baseline]
    2_0_*        → []                            （源已是新版，无需过滤）

    仅返回真正可达（能查到 java_classes 且非空）的库；不可达的静默丢弃。
    返回 list[str]。空 list 表示迁移过滤不生效。
    """
    s = (schema or "").strip()
    if s.startswith("2_0"):
        return []
    if s.startswith("1_0_") and s != "1_0_baseline":
        site = s[len("1_0_"):]
        cands = [f"2_0_{site}", "2_0_baseline"]
    else:
        cands = ["2_0_baseline"]

    result, seen = [], set()
    for c in cands:
        if c in seen:
            continue
        seen.add(c)
        try:
            rows = q(c, "SELECT COUNT(*) AS cnt FROM java_classes")
            if rows and rows[0].get("cnt", 0) > 0:
                result.append(c)
        except Exception:
            continue
    return result


def _is_migrated_any(migrated_schemas, fqn, cache=None):
    """单点迁移判定（BFS 内用，带 cache 去重）。

    与 analyzer.py:TgtDB.has_class 行为对齐：取 fqn 的 simple_name（最后一段），
    在任一 migrated_schema.java_classes WHERE class_name=simple_name 命中即视为已迁移。
    schema 不可达（DB error）时该库跳过（保守，不阻断其余库判定）。
    """
    if not migrated_schemas or not fqn:
        return False
    if cache is not None and fqn in cache:
        return cache[fqn]
    simple = fqn.rsplit(".", 1)[-1]
    result = False
    if simple:
        for tgt in migrated_schemas:
            try:
                rows = q(tgt,
                    "SELECT 1 FROM java_classes WHERE class_name=%s LIMIT 1",
                    (simple,))
                if rows:
                    result = True
                    break
            except Exception:
                continue
    if cache is not None:
        cache[fqn] = result
    return result


def _partition_migrated(migrated_schemas, fqns):
    """批量把 fqns 划分为 (migrated, remaining)，按简单类名匹配。

    收集文件前的兜底过滤：special["all"] 这条路径完全绕过了 BFS 的迁移判定，
    若不在这里再过一遍，已迁移的特殊类文件仍会进入结果集。
    """
    fqns = {f for f in fqns if f}
    if not migrated_schemas or not fqns:
        return set(), set(fqns)

    by_simple = {}
    for f in fqns:
        by_simple.setdefault(f.rsplit(".", 1)[-1], set()).add(f)
    simples = sorted(by_simple.keys())

    migrated, BATCH = set(), 500
    for tgt in migrated_schemas:
        hit = set()
        try:
            for i in range(0, len(simples), BATCH):
                chunk = simples[i:i + BATCH]
                ph = ",".join(["%s"] * len(chunk))
                rows = q(tgt,
                    f"SELECT DISTINCT class_name FROM java_classes "
                    f"WHERE class_name IN ({ph})", tuple(chunk))
                hit |= {(r.get("class_name") or "") for r in rows}
        except Exception:
            continue
        for s in hit:
            migrated |= by_simple.get(s, set())
    return migrated, fqns - migrated


def _bfs_import_graph(schema, seeds, migrated_schemas=None, max_nodes=5000):
    """analyzer.py 的 import 图 BFS。从 seeds 出发，沿 java_classes.imports
    字段展开，对 interface 节点补实现类。

    migrated_schemas: 2.0 对照库列表（由 _derive_migrated_schemas 推导）。
        命中迁移的 FQN **整个跳过**——既不写入 all_cls（不收集 file_path），
        也不展开其 imports。这与旧实现的关键区别在于：旧实现仍把已迁移类
        记入 all_cls 让 file_path 被收集，导致结果膨胀（1.0 文件被误报）。

        行为对齐 analyzer.py:run_entity：`tgt.has_class(simple_name)` 命中 →
        视为已迁移 → continue（不展开、不收集）。

        若 migrated_schemas 为空，行为与旧版一致（不检查迁移状态）。

    返回 (all_cls: dict[fqn -> row], migrated_seen: set[fqn])。
    """
    migrated_schemas = migrated_schemas or []
    all_cls = {}
    migrated_seen = set()
    cache = {}
    visited = set(seeds)
    queue = list(seeds)
    while queue and len(all_cls) < max_nodes:
        fqn = queue.pop(0)
        if fqn.endswith(".*"):
            continue
        # 关键修复：已迁移 → 整个跳过（不收集 file_path、不展开 imports）。
        # 种子也不再豁免：若 L1 类已迁移到 2.0，其 1.0 文件不应作为影响输出。
        if migrated_schemas and _is_migrated_any(migrated_schemas, fqn, cache):
            migrated_seen.add(fqn)
            continue
        rows = q(schema,
            "SELECT * FROM java_classes WHERE full_qualified_name=%s", (fqn,))
        if not rows:
            continue
        row = rows[0]
        all_cls[fqn] = row
        # 展开 imports 字段
        for i in (row.get("imports") or "").split(","):
            i = i.strip()
            if i and i not in visited:
                visited.add(i)
                queue.append(i)
        # interface 补实现类
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
                               (impl.get("implements_interfaces") or "").split(",")
                               if x.strip()}
                if iface_name not in impl_ifaces:
                    continue
                impl_imports = {x.strip() for x in
                                (impl.get("imports") or "").split(",")
                                if x.strip()}
                impl_pkg = (impl.get("package_name") or "").strip()
                if fqn not in impl_imports and impl_pkg != iface_pkg:
                    continue
                impl_fqn = (impl.get("full_qualified_name") or "").strip()
                if impl_fqn and impl_fqn not in visited:
                    visited.add(impl_fqn)
                    queue.append(impl_fqn)
    return all_cls, migrated_seen


def _class_exists_in_other_schema(source_schema, target_schema, fqn):
    """检查 target_schema 的 java_classes 表中是否有与 fqn 同名简单类名的类。

    与 analyzer.py:TgtDB.has_class 行为对齐：
    - 取 fqn 的 simple_name（最后一段）
    - 在 target_schema.java_classes WHERE class_name=simple_name 中查
    - schema 不可达（DB error）时返回 False（不阻断，保守）

    注：BFS 已改用 _is_migrated_any（支持多对照库 + cache），此函数保留供
    其它调用方/向后兼容使用。
    """
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


def _collect_java_files_from_fqns(schema, fqns):
    """FQN 集合反查 java_classes.file_path。"""
    if not fqns:
        return []
    fqns = list(fqns)
    placeholders = ",".join(["%s"] * len(fqns))
    rows = q(schema,
        f"SELECT DISTINCT file_path FROM java_classes "
        f"WHERE full_qualified_name IN ({placeholders}) "
        f"AND file_path IS NOT NULL AND file_path<>''",
        tuple(fqns))
    return [r["file_path"] for r in rows]


def _collect_xml_paths(schema, flow_ids, chain_ids, bean_ids):
    """跨表收集 xml_path：flows/states/activities/transitions +
    logics/logic_steps/bridges + beans + module_parameters。"""
    paths = set()

    def _add(p):
        if p and p.strip():
            paths.add(p.strip())

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
    # 注：module_parameters 表的 xml_path **不**通过 SQL 收集。
    # 这些是 resources/{module-parameter, namingsql}/*.xml，
    # 索引时 module_id 与 bean_id/bridge_id 命名空间不同（module_id 是配置命名空间），
    # 无法用 SQL 精确反推。改由 _scan_resource_files (Plan B, codeBaseRoot) 收集。
    return sorted(paths)


def _find_dynamic_chain_ids(schema, fqns):
    """Fix-E 动态 chain：扫描 method_bodies / source_text 中
    setChainId("...") 字面量。字段不存在时静默返回空集合。"""
    pattern = re.compile(r'setChainId\s*\(\s*"([^"]+)"')
    out = set()
    for fqn in fqns:
        try:
            row = q(schema,
                "SELECT method_bodies, source_text FROM java_classes "
                "WHERE full_qualified_name=%s", (fqn,))
        except Exception:
            return out
        if not row:
            continue
        text = ((row[0].get("method_bodies") or "")
                + " " + (row[0].get("source_text") or ""))
        for m in pattern.finditer(text):
            out.add(m.group(1))
    return out


def _scan_resource_files(code_base_root, xml_paths):
    """复用 analyzer.py:scan_resource_files (line 593-616) 逻辑。
    对每个 xml_path 找 \\resources\\ 之前的根，os.walk 扫描
    {root}/resources/{module-parameter, namingsql}/*.xml。
    返回相对于 code_base_root 的路径列表。"""
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


# ── 子工程锚定的 namingsql 收窄 ──────────────────────────────────────
# 与 analyzer_compat.scan_module_parameters (line 682-719) 共享 'codes\\<subdir>\\'
# 锚点规则。区别：本函数走文件系统 (os.walk)，不依赖 MySQL，调用方是
# search_service_impact 在传 codeBaseRoot 时启用的 Plan C 收窄 pass。
_CODES_ANCHOR = "codes\\"


def _derive_subproject_roots(xml_paths, code_base_root):
    """从 entry 链 xml_paths + codeBaseRoot 推出 namingsql 扫描起点。

    对每个 xml_path，取 'codes\\<sub>\\' 之前的全部相对前缀，拼到 codeBaseRoot 后。
    返回 {subdir: abs_root_path} 字典；abs_root_path 不存在由调用方按 isdir 判断。
    """
    roots = {}
    base = (code_base_root or "").rstrip("\\/").replace("/", "\\")
    for p in xml_paths or []:
        norm = (p or "").replace("/", "\\")
        idx = norm.find(_CODES_ANCHOR)
        if idx < 0:
            continue
        tail = norm[idx + len(_CODES_ANCHOR):]
        end = tail.find("\\")
        if end <= 0:
            continue
        subdir = tail[:end].strip()
        if not subdir or subdir in roots:
            continue
        prefix = norm[:idx]  # 'codes\\' 之前的所有相对段
        abs_root = (os.path.join(base, prefix, "codes", subdir) if prefix
                    else os.path.join(base, "codes", subdir))
        roots[subdir] = abs_root
    return roots


def _scan_namingsql_by_subproject(code_base_root, subproject_roots):
    """对每个 (subdir, abs_root) 在 abs_root 下 os.walk，收集 namingsql/*.xml。

    返回相对 code_base_root 的 '\\\\' 风格路径列表（去重）。"""
    seen, result = set(), []
    for sub, abs_root in sorted((subproject_roots or {}).items()):
        if not abs_root or not os.path.isdir(abs_root):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_root):
            if os.path.basename(dirpath) == "namingsql":
                for fn in sorted(filenames):
                    # namingsql 文件名约定为 *.naming-sql.xml，避开模块下其它 XML
                    # (例如 mapper 注册、方言 SQL 等)。
                    if fn.lower().endswith(".naming-sql.xml"):
                        rp = os.path.relpath(
                            os.path.join(dirpath, fn), code_base_root)
                        rp = rp.replace("/", "\\")
                        if rp not in seen:
                            seen.add(rp)
                            result.append(rp)
                dirnames.clear()  # namingsql 目录收完不再下钻
    return result


def _explore_phase(schema, entry_point, commandId, flowId, maxDepth, warnings):
    """analyzer.py 等价的 MySQL 实现——通过 analyzer_compat 委托。

    完整算法在 analyzer_compat.run_entity / run_flow 中:
      1. chain 递归展开 (REF_CHAIN)
      2. bean 派生 (L1 FQN)
      3. 特殊类发现 (Fix-B/C/D)
      4. import 图 BFS（迁移类整个跳过）
      5. Fix-E 动态 chain
      6. file_path / xml_path 收集（含 L2 排除）

    返回 (pre_files: set[str], extra_warnings: list[str])。"""
    from analyzer_compat import run_entity, run_flow
    pre_files = set()
    extra_warnings = []

    # 2.0 对照库固定为 2_0_baseline（analyzer.py 等价）
    tgt_schema = "2_0_baseline"

    if commandId:
        result = run_entity(
            schema=schema, tgt_schema=tgt_schema,
            command_id=commandId, q_fn=q,
            code_base_root=None,
        )
    elif flowId:
        result = run_flow(
            schema=schema, tgt_schema=tgt_schema,
            flow_id=flowId, q_fn=q,
            code_base_root=None,
        )
    else:
        extra_warnings.append("commandId 与 flowId 都未提供")
        return pre_files, extra_warnings

    pre_files = set(result.get("files", []))
    extra_warnings.extend(result.get("warnings", []))
    return pre_files, extra_warnings


if __name__ == "__main__":
    print(f"[mm-codegraph] 启动成功，stdio 就绪", file=sys.stderr)
    mcp.run()  # 默认 stdio transport，适配 Claude Code