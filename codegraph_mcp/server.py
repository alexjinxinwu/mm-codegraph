#!/usr/bin/env python3
"""MCP server — stdio transport adapter, delegates all query logic to codegraph-core."""

import os
import re
from collections import defaultdict
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Query primitives delegate to codegraph-core
from codegraph_core.query_engine import (
    get_pool,
    q,
    out,
    sql_query,
    ALL_TABLES,
)

mcp = FastMCP("mm-codegraph")


# ── Navigation ────────────────────────────────────────────────────────

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


# ── Service Entries ───────────────────────────────────────────────────

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


# ── Flows / States ─────────────────────────────────────────────────────

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


# ── Logic Chains ──────────────────────────────────────────────────────

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


# ── Beans / Java ──────────────────────────────────────────────────────

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


# ── Raw SQL ───────────────────────────────────────────────────────────

@mcp.tool()
def raw_sql_query(schema: str, sql: str, limit: int = 200) -> str:
    """在指定 schema 执行只读查询（上面工具无法覆盖时使用）。仅允许单条 SELECT/WITH。"""
    return out(sql_query(schema, sql, limit))


# ── Service Impact Search ─────────────────────────────────────────────

# Import analyzer_compat from codegraph-core (injected at runtime)
from codegraph_core.analyzer_compat import run_entity, run_flow


@mcp.tool()
def search_service_impact(
    schema: str,
    commandId: str = None,
    flowId: str = None,
    direction: str = "both",
    maxDepth: int = 20,
    codeBaseRoot: str = None,
) -> str:
    """搜索服务影响范围。基于 13 张表的 ER 关系遍历 + analyzer_compat.py 启发式
    （Fix-B/C/D 特殊类 + REF_CHAIN 递归 + import 图 BFS + 动态 chain +
    可选资源目录扫描），输出受影响文件列表。"""
    if not commandId and not flowId:
        raise ValueError("At least one of commandId or flowId must be provided")
    if direction not in ("forward", "backward", "both"):
        raise ValueError("direction must be one of: forward, backward, both")
    if maxDepth <= 0:
        raise ValueError("maxDepth must be a positive integer")
    if codeBaseRoot is not None and codeBaseRoot != "":
        if not isinstance(codeBaseRoot, str):
            raise ValueError("codeBaseRoot must be a string or None")
        if not os.path.isabs(codeBaseRoot):
            raise ValueError(f"codeBaseRoot must be an absolute path: {codeBaseRoot!r}")
        if not os.path.isdir(codeBaseRoot):
            raise ValueError(f"codeBaseRoot does not exist or is not a directory: {codeBaseRoot!r}")
    if not codeBaseRoot:
        env_root = os.environ.get("MM_CODEGRAPH_CODEBASE_ROOT", "").strip()
        if env_root and os.path.isdir(env_root):
            codeBaseRoot = env_root

    entry_point = commandId or flowId
    warnings = []

    # Use analyzer_compat from codegraph-core
    def _q_fn(schema_str, sql, params=()):
        return q(schema_str, sql, params)

    if commandId:
        result = run_entity(schema, None, commandId, _q_fn,
                           code_base_root=codeBaseRoot, max_depth=maxDepth)
    else:
        result = run_flow(schema, None, flowId, _q_fn, code_base_root=codeBaseRoot)

    return out(result)