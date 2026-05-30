#!/usr/bin/env python3
"""MCP server: 把 MySQL 代码知识图谱暴露给 Claude Code 用于代码分析。"""

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
            host=os.environ.get("MYSQL_HOST", "192.168.97.2"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "w00558136"),
            password=os.environ.get("MYSQL_PASSWORD", "Huawei@123"),
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
) -> str:
    """搜索服务影响范围。基于 13 张表的 ER 关系遍历，输出受影响文件列表。

    Args:
        schema: 数据库 schema
        commandId: 服务入口 command_id（可选，二选一）
        flowId: 流程 ID（可选，二选一）
        direction: 遍历方向 forward/backward/both
        maxDepth: 最大遍历深度（默认 20）
    """
    # 参数校验
    if not commandId and not flowId:
        raise ValueError("At least one of commandId or flowId must be provided")
    if direction not in ("forward", "backward", "both"):
        raise ValueError("direction must be one of: forward, backward, both")
    if maxDepth <= 0:
        raise ValueError("maxDepth must be a positive integer")

    entry_point = commandId or flowId

    # 查找入口 service_entry
    entry = None
    if commandId:
        entries = q(schema,
            "SELECT * FROM service_entries WHERE command_id=%s LIMIT 1", (commandId,))
        if entries:
            entry = entries[0]
    elif flowId:
        entries = q(schema,
            "SELECT * FROM service_entries WHERE flow_id=%s LIMIT 1", (flowId,))
        if entries:
            entry = entries[0]

    if not entry:
        return out({
            "entryPoint": entry_point,
            "direction": direction,
            "totalImpacted": 0,
            "files": [],
            "impactChain": [],
            "warnings": [f"No service entry found for {commandId or flowId}"],
        })

    visited = set()
    files = {}  # {path: {"path": path, "type": type}}
    edges = []  # [{"from": "type:id", "to": "type:id"}]
    warnings = []

    if direction in ("forward", "both"):
        _traverse_forward(schema, entry, visited, 0, maxDepth, files, edges, warnings)
    if direction in ("backward", "both"):
        _traverse_backward(schema, entry, visited, 0, maxDepth, files, edges, warnings)

    result = {
        "entryPoint": entry_point,
        "direction": direction,
        "totalImpacted": len(files),
        "files": list(files.values()),
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

        # 沿 flow_id 遍历 flows
        if node.get("flow_id"):
            flows = q(schema, "SELECT * FROM flows WHERE flow_id=%s", (node["flow_id"],))
            for flow in flows:
                flow["table"] = "flow"
                _add_edge(edges, node_key, f"flow:{flow['flow_id']}")
                _traverse_forward(schema, flow, visited, depth + 1, max_depth, files, edges, warnings)

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
            "SELECT * FROM bridges WHERE chain_id=%s ORDER BY step_order, bridge_order",
            (chain_id,))
        for bridge in bridges:
            bridge["table"] = "bridge"
            _add_edge(edges, node_key, f"bridge:{bridge['bridge_id']}")
            _traverse_forward(schema, bridge, visited, depth + 1, max_depth, files, edges, warnings)

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

    elif table in ("flow", "logic", "bridge", "bean", "state", "activity"):
        # 通用反向查找实现
        pass  # 简化：主要通过 service_entry 的 flow_id/chain_id 反向查找


def _collect_files(schema, node, files):
    """收集节点关联的文件路径"""
    # 收集 xml_path
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


def _add_edge(edges, from_key, to_key):
    """添加边，避免重复"""
    edge = {"from": from_key, "to": to_key}
    if edge not in edges:
        edges.append(edge)


if __name__ == "__main__":
    host = os.environ.get("MYSQL_HOST", "192.168.97.2")
    port = os.environ.get("MYSQL_PORT", "3306")
    try:
        get_pool().connection().close()
    except Exception as exc:
        print(f"[mm-codegraph] 启动失败：无法连接 MySQL {host}:{port}（{exc}）", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"[mm-codegraph] 启动成功，stdio 就绪，MySQL {host}:{port}", file=sys.stderr)
    mcp.run()  # 默认 stdio transport，适配 Claude Code