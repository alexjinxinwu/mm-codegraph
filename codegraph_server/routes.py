"""HTTP routes mapping to QueryEngine primitives.

These endpoints provide the same query semantics as the MCP server,
ensuring zero behavioral difference between MCP stdio and HTTP transports.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from codegraph_core.graph.expand_service import expand_neighbors
from codegraph_core.graph.resolve_service import resolve_entry
from codegraph_core.query_engine import get_pool, q, out, sql_query, ALL_TABLES
from codegraph_core.analyzer_compat import run_entity, run_flow
from codegraph_server.schemas_expand import ExpandRequest, ExpandResponse, GraphEdge, GraphNode, NodeRef
from codegraph_server.schemas_resolve import GraphNodeOut, ResolveResponse

router = APIRouter(prefix="/api/v1", tags=["codegraph"])


@router.post("/expand", response_model=ExpandResponse)
def expand(body: ExpandRequest):
    """Expand forward neighbors of a graph node using graph-core EDGE_RULES."""
    try:
        result = expand_neighbors(
            body.schema_, body.node.type, body.node.id, body.edgeIds
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ExpandResponse(
        nodes=[GraphNode(**n) for n in result.nodes],
        edges=[GraphEdge(**e) for e in result.edges],
    )


@router.get("/resolve", response_model=ResolveResponse)
def resolve_entry_route(schema: str, kind: str, value: str):
    """Resolve an external identifier to graph root node(s)."""
    try:
        result = resolve_entry(schema, kind, value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ResolveResponse(
        status=result.status,
        roots=[GraphNodeOut(**n) for n in result.roots],
        candidates=[GraphNodeOut(**n) for n in result.candidates],
    )


# ── Query Engine Primitives ───────────────────────────────────────────

@router.get("/pool")
def get_pool_info():
    """Return current connection pool status."""
    pool = get_pool()
    return {"pool": "active", "max_connections": pool.maxconnections}


@router.post("/q")
def query(schema: str, sql: str, params: Optional[list] = None):
    """Execute a query against the specified schema.

    Identical behavior to QueryEngine.q() — same connection pool,
    same schema validation, same result format.
    """
    result = q(schema, sql, tuple(params) if params else ())
    return result


@router.get("/schema")
def schema_info(schema: str):
    """Return schema name (validates the schema name)."""
    from codegraph_core.schema_validator import SchemaValidator
    validated = SchemaValidator.validate(schema)
    return {"schema": validated}


@router.post("/out")
def format_out(data: dict):
    """Format data as JSON — identical to QueryEngine.out()."""
    return out(data)


# ── Navigation ─────────────────────────────────────────────────────────

@router.get("/schemas")
def list_schemas():
    """List all code graph schemas on this instance."""
    conn = get_pool().connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            dbs = [r["Database"] for r in cur.fetchall()]
    finally:
        conn.close()
    system = {"information_schema", "mysql", "performance_schema", "sys"}
    return [d for d in dbs if d not in system]


@router.get("/schemas/{schema}/overview")
def schema_overview(schema: str):
    """Return row counts for all tables in the schema."""
    result = {}
    for t in ALL_TABLES:
        try:
            result[t] = q(schema, f"SELECT COUNT(*) AS c FROM `{t}`")[0]["c"]
        except Exception as e:
            result[t] = f"error: {e}"
    return result


@router.get("/schemas/{schema}/search")
def search(schema: str, keyword: str = "", limit: int = 20):
    """Cross-table keyword search across service_entries, flows, beans, java_classes."""
    like = f"%{keyword}%"
    return {
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
    }


# ── Service Entries ──────────────────────────────────────────────────────

@router.get("/schemas/{schema}/service-entries")
def find_service_entry(schema: str, keyword: str = "", limit: int = 50):
    """Find service entries by name/uri/command_id/business_type."""
    if keyword:
        like = f"%{keyword}%"
        return q(schema,
            "SELECT * FROM service_entries WHERE name LIKE %s OR uri LIKE %s "
            "OR command_id LIKE %s OR business_type LIKE %s LIMIT %s",
            (like, like, like, like, limit))
    return q(schema, "SELECT * FROM service_entries LIMIT %s", (limit,))


@router.get("/schemas/{schema}/service-entries/{name}")
def get_service_entry(schema: str, name: str):
    """Get service entry details with linked flow, logic chain, and bean."""
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
    return {"service_entries": entries, "linked": linked}


# ── Flows / States ────────────────────────────────────────────────────

@router.get("/schemas/{schema}/flows/{flow_id}")
def get_flow(schema: str, flow_id: str):
    """Get flow details with states and flow_tasks."""
    return {
        "flow": q(schema, "SELECT * FROM flows WHERE flow_id=%s", (flow_id,)),
        "states": q(schema,
            "SELECT * FROM states WHERE flow_id=%s ORDER BY state_order", (flow_id,)),
        "flow_tasks": q(schema,
            "SELECT * FROM flow_tasks WHERE flow_id=%s ORDER BY task_order", (flow_id,)),
    }


@router.get("/schemas/{schema}/flows/{flow_id}/states/{state_name}")
def get_state(schema: str, flow_id: str, state_name: str):
    """Get activities and transitions for a specific state."""
    return {
        "activities": q(schema,
            "SELECT * FROM activities WHERE flow_id=%s AND state_name=%s ORDER BY activity_order",
            (flow_id, state_name)),
        "transitions": q(schema,
            "SELECT * FROM transitions WHERE flow_id=%s AND state_name=%s",
            (flow_id, state_name)),
    }


@router.get("/schemas/{schema}/flows/{flow_id}/statemachine")
def get_flow_statemachine(schema: str, flow_id: str):
    """Get full state machine view for a flow."""
    from collections import defaultdict
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
    return {"flow_id": flow_id, "state_machine": sm}


# ── Logic Chains ──────────────────────────────────────────────────────

@router.get("/schemas/{schema}/chains/{chain_id}")
def resolve_chain(schema: str, chain_id: str):
    """Resolve logic chain: logics + logic_steps + bridges + resolved java_classes."""
    import re
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
    return {"logics": logics, "logic_steps": steps,
            "bridges": bridges, "resolved_classes": classes}


# ── Beans / Java ──────────────────────────────────────────────────────

@router.get("/schemas/{schema}/beans")
def find_bean(schema: str, keyword: str = "", limit: int = 50):
    """Find beans by bean_id or bean_class."""
    like = f"%{keyword}%"
    return q(schema,
        "SELECT * FROM beans WHERE bean_id LIKE %s OR bean_class LIKE %s LIMIT %s",
        (like, like, limit))


@router.get("/schemas/{schema}/classes")
def find_class(schema: str, keyword: str = "", exact: bool = False, limit: int = 50):
    """Find Java classes by name or FQN."""
    cols = ("id, class_name, package_name, full_qualified_name, file_path, "
            "is_interface, is_abstract, is_enum, super_class_fqn")
    if exact:
        return q(schema,
            f"SELECT {cols} FROM java_classes WHERE full_qualified_name=%s LIMIT %s",
            (keyword, limit))
    like = f"%{keyword}%"
    return q(schema,
        f"SELECT {cols} FROM java_classes "
        "WHERE class_name LIKE %s OR full_qualified_name LIKE %s LIMIT %s",
        (like, like, limit))


@router.get("/schemas/{schema}/classes/{fqn}")
def get_class(schema: str, fqn: str, include_methods: bool = True):
    """Get class details with methods, subclasses, implementors, and beans."""
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
    return result


@router.get("/schemas/{schema}/methods")
def find_method(schema: str, method_name: str = "", class_fqn: str = "", limit: int = 100):
    """Find Java methods by name and/or class FQN."""
    conds, params = [], []
    if method_name:
        conds.append("method_name = %s"); params.append(method_name)
    if class_fqn:
        conds.append("class_fqn = %s"); params.append(class_fqn)
    where = " AND ".join(conds) if conds else "1=1"
    params.append(limit)
    return q(schema,
        "SELECT class_fqn, method_name, full_signature, modifiers, annotations "
        f"FROM java_methods WHERE {where} LIMIT %s", tuple(params))


# ── Raw SQL ───────────────────────────────────────────────────────────

@router.post("/schemas/{schema}/sql")
def raw_sql(schema: str, sql: str, limit: int = 200):
    """Execute raw read-only SQL query with safety checks."""
    return sql_query(schema, sql, limit)


# ── Service Impact ────────────────────────────────────────────────────

@router.get("/service-impact")
def service_impact(
    schema: str,
    commandId: Optional[str] = None,
    flowId: Optional[str] = None,
    maxDepth: int = 1,
    codeBaseRoot: Optional[str] = None,
):
    """Search service impact using analyzer_compat from codegraph-core.

    Identical behavior to the MCP search_service_impact tool.
    """
    if not commandId and not flowId:
        raise ValueError("At least one of commandId or flowId must be provided")

    def _q_fn(schema_str, sql, params=()):
        return q(schema_str, sql, params)

    if commandId:
        return run_entity(schema, None, commandId, _q_fn,
                         code_base_root=codeBaseRoot, max_depth=maxDepth)
    return run_flow(schema, None, flowId, _q_fn, code_base_root=codeBaseRoot)