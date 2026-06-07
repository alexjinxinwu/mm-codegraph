# Node Expand API Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Expose graph forward expansion as **POST `/api/v1/expand`**, orchestrating graph-core (`hydrate` → `build_expand_query` → `q()`) into `{ nodes, edges }` for incremental canvas merging.

**Architecture:** Business logic in `codegraph_core/graph/expand_service.py` (reusable by future MCP). FastAPI route in `codegraph_server/routes.py` validates request, delegates to service. No changes to EDGE_RULES or `build_expand_query`.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, pytest, graph-core, `QueryEngine.q()`

**Spec refs:** `openspec/changes/add-node-expand-api/specs/graph-api/spec.md`

**nodeType convention:** Use graph-core names (`flow`, `bean`, `state`, `logic`, `bridge` — not plural table names). Fix delta spec typos (`flows`→`flow`) during apply if still present.

---

## Task 1: Request/response models & validation helpers (tasks §1)

- [ ] **Step 1:** Create `codegraph_server/schemas_expand.py` (or `codegraph_core/graph/expand_models.py`) with Pydantic models:

```python
class NodeRef(BaseModel):
    type: str
    id: int = Field(gt=0)

class ExpandRequest(BaseModel):
    schema: str
    node: NodeRef
    edgeIds: list[str] | None = None

class GraphNode(BaseModel):
    type: str
    id: int
    title: str | None = None
    subtitle: str | None = None

class GraphEdge(BaseModel):
    ruleId: str
    from_: NodeRef = Field(alias="from")
    to: NodeRef
    label: str
    model_config = ConfigDict(populate_by_name=True)

class ExpandResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
```

- [ ] **Step 2:** Create `codegraph_core/graph/expand_validation.py` with pure functions (no DB):

```python
def validate_expand_input(schema: str, node_type: str, node_id: int, edge_ids: list[str] | None) -> None:
    SchemaValidator.validate(schema)  # raises ValueError
    if get_node_spec(node_type) is None:
        raise ValueError(f"Unknown node type: {node_type}")
    if edge_ids:
        for rid in edge_ids:
            rule = get_edge_rule(rid)
            if rule is None:
                raise ValueError(f"Unknown edge rule: {rid}")
            if rule.from_type != node_type:
                raise ValueError(f"Edge {rid} not applicable to {node_type}")
```

- [ ] **Step 3:** Create `codegraph_core/graph/test_expand_validation.py` — unknown type, bad edgeId, edgeId.from mismatch, invalid schema → raises before any `q()` call
- [ ] **Step 4:** Run: `pytest codegraph_core/graph/test_expand_validation.py -v`
- [ ] **Step 5:** Commit: `feat(expand): add expand request validation helpers`

---

## Task 2: Hydrate + source-column union (tasks §2)

- [ ] **Step 1:** In `expand_service.py`, add helpers (RED tests first in `test_expand_service.py`):

```python
EXPAND_NEIGHBOR_LIMIT = 200

def _source_columns_for_type(node_type: str) -> set[str]:
    cols: set[str] = set()
    for rule in get_edges_from(node_type):
        for src, _ in rule.match:
            cols.add(src)
    return cols

def hydrate_node(schema: str, node_type: str, node_id: int, q_fn=q) -> dict | None:
    spec = get_node_spec(node_type)
    src_cols = _source_columns_for_type(node_type)
    select_cols = sorted({spec.id_column, spec.title, spec.subtitle} | src_cols)
    quoted = ", ".join(f"`{c}`" for c in select_cols)
    sql = f"SELECT {quoted} FROM `{spec.table}` WHERE `{spec.id_column}` = %s LIMIT 1"
    rows = q_fn(schema, sql, (node_id,))
    return rows[0] if rows else None
```

- [ ] **Step 2:** Tests with mocked `q_fn`:
  - `test_hydrate_flow_includes_flow_id` — flow type SELECT includes `flow_id`
  - `test_hydrate_bridge_includes_before_beans` — guard source col present
  - `test_hydrate_not_found` — empty rows → `None`
  - `test_hydrate_uses_bound_params` — assert params tuple `(node_id,)`, id not in SQL string

- [ ] **Step 3:** Run tests RED then GREEN
- [ ] **Step 4:** Commit: `feat(expand): add node hydration for expand`

---

## Task 3: Expand orchestration — shape, dedupe, limit (tasks §3–§5)

- [ ] **Step 1:** Add to `expand_service.py`:

```python
@dataclass
class ExpandResult:
    nodes: list[dict]
    edges: list[dict]

def expand_neighbors(
    schema: str,
    node_type: str,
    node_id: int,
    edge_ids: list[str] | None = None,
    limit: int = EXPAND_NEIGHBOR_LIMIT,
    q_fn=q,
) -> ExpandResult:
    validate_expand_input(schema, node_type, node_id, edge_ids)
    row = hydrate_node(schema, node_type, node_id, q_fn=q_fn)
    if row is None:
        return ExpandResult(nodes=[], edges=[])
    rules = get_edges_from(node_type)
    if edge_ids:
        allowed = set(edge_ids)
        rules = [r for r in rules if r.id in allowed]
    # loop rules → build_expand_query → q_fn → shape nodes/edges → dedupe
```

- [ ] **Step 2:** Implement `_shape_neighbor(rule, row, neighbor_row) -> (node_dict, edge_dict)` using target NodeSpec for `type/id/title/subtitle`

- [ ] **Step 3:** Dedupe: nodes by `(type, id)`; edges by `(ruleId, from.type, from.id, to.type, to.id)`

- [ ] **Step 4:** Tests in `test_expand_service.py` (mock `q_fn` returning canned rows):
  - `test_expand_flow_states` — single edge `flow.states`, one state neighbor
  - `test_expand_bean_java_class` — aliased column path
  - `test_expand_state_activities` — composite key
  - `test_expand_logic_activities` — semantic edge
  - `test_expand_bridge_beans_guard` — guard IN
  - `test_expand_default_all_edges` — no edgeIds, multiple rules invoked
  - `test_expand_filtered_edge_ids` — only requested rule
  - `test_expand_dedupe_nodes` — same neighbor from two rules → one node, two edges
  - `test_expand_not_found_empty` — hydrate returns None
  - `test_expand_limit_passed_to_build_expand_query` — verify limit arg

- [ ] **Step 5:** Run: `pytest codegraph_core/graph/test_expand_service.py -v`
- [ ] **Step 6:** Export `expand_neighbors` from `codegraph_core/graph/__init__.py`
- [ ] **Step 7:** Commit: `feat(expand): add expand_neighbors orchestration`

---

## Task 4: HTTP route POST /api/v1/expand (tasks §1.1)

- [ ] **Step 1:** Add to `codegraph_server/routes.py`:

```python
@router.post("/expand", response_model=ExpandResponse)
def expand(body: ExpandRequest):
    try:
        result = expand_neighbors(
            body.schema, body.node.type, body.node.id, body.edgeIds
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ExpandResponse(nodes=result.nodes, edges=result.edges)
```

- [ ] **Step 2:** Wire imports from `codegraph_core.graph.expand_service` and schemas module
- [ ] **Step 3:** Create `codegraph_server/test_expand_route.py` with FastAPI `TestClient`:
  - Patch `expand_neighbors` or `q` — happy path 200 + JSON shape
  - Unknown node type → 422, expand_neighbors not called (mock assert)
  - Invalid edgeId → 422
  - Not found → 200 empty lists

- [ ] **Step 4:** Run: `PYTHONPATH=. pytest codegraph_server/test_expand_route.py codegraph_core/graph/test_expand*.py -v`
- [ ] **Step 5:** Commit: `feat(expand): add POST /api/v1/expand endpoint`

---

## Task 5: Spec alignment & integration smoke (tasks §6)

- [ ] **Step 1:** Fix delta spec typos in `specs/graph-api/spec.md`:
  - `flows` → `flow`, `beans` → `bean`, `states` → `state`, `logics` → `logic`, `bridges` → `bridge`
  - `from 为 flows` → `from 为 flow`

- [ ] **Step 2:** Manual smoke (requires MySQL or skip if unavailable):

```bash
PYTHONPATH=. uvicorn codegraph_server.app:app --port 8000
curl -X POST http://localhost:8000/api/v1/expand \
  -H 'Content-Type: application/json' \
  -d '{"schema":"YOUR_SCHEMA","node":{"type":"flow","id":1},"edgeIds":["flow.states"]}'
```

- [ ] **Step 3:** Run full test suite:

```bash
PYTHONPATH=. pytest codegraph_core/graph/ codegraph_server/test_expand_route.py -v --tb=short
```

- [ ] **Step 4:** Mark `tasks.md` checkboxes as sections complete during apply
- [ ] **Step 5:** Commit: `docs(openspec): fix graph-api spec nodeType names`

---

## Task 6: Final verification before `/opsx:verify`

- [ ] **Step 1:** Grep — no hand-written expand SQL outside `expand_service.py` / `build_expand_query`
- [ ] **Step 2:** Confirm all 12 test scenarios in tasks §6 have matching test functions
- [ ] **Step 3:** Confirm validation paths never call `q()` (use mock assert in route tests)
- [ ] **Step 4:** Run `pytest codegraph_core/graph/ codegraph_server/test_expand_route.py -v`

---

## Apply checklist mapping

| tasks.md section | Plan task |
|------------------|-----------|
| §1 端点与校验     | Task 1, 4 |
| §2 水合           | Task 2    |
| §3 forward 展开   | Task 3    |
| §4 整形去重封顶   | Task 3    |
| §5 防护           | Task 2–3  |
| §6 测试           | Tasks 2–5 |

After apply completes, run `/opsx:verify` to produce `verify.md`.
