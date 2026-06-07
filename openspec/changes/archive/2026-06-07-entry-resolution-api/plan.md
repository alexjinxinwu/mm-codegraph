# Entry Resolution API Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Expose **GET `/api/v1/resolve`** to map external identifiers (commandId, flowId) to graph root nodes with three-state semantics (notFound / found / multiple), compatible with `/expand` input shape.

**Architecture:** Declarative `ENTRY_RESOLVERS` in `codegraph_core/graph/`; `resolve_entry()` builds parameterized SELECT, shapes rows via shared `shape_node()`; FastAPI route thin-wraps validation. Refactor expand to reuse `shape_node()` where practical.

**Tech Stack:** Python 3, FastAPI, Pydantic, pytest, graph-core NodeSpec, `QueryEngine.q()`

**Spec refs:** `openspec/changes/entry-resolution-api/specs/graph-api/spec.md`

**nodeType convention:** Use graph-core names (`service_entry`, `flow`) — not table names (`service_entries`, `flows`). Fix delta spec during apply.

---

## Task 1: Shared node shaping (prerequisite for expand parity)

- [ ] **Step 1:** Create `codegraph_core/graph/shape.py`:

```python
def shape_node(node_type: str, row: dict) -> dict:
    spec = get_node_spec(node_type)
    if spec is None:
        raise ValueError(f"Unknown node type: {node_type}")
    return {
        "type": node_type,
        "id": row[spec.id_column],
        "title": row.get(spec.title),
        "subtitle": row.get(spec.subtitle),
    }
```

- [ ] **Step 2:** Create `codegraph_core/graph/test_shape.py` — shape flow row → correct type/id/title/subtitle
- [ ] **Step 3:** Refactor `expand_service.py` `_shape_neighbor` to use `shape_node(rule.to_type, neighbor_row)` for node dict
- [ ] **Step 4:** Run: `pytest codegraph_core/graph/test_shape.py codegraph_core/graph/test_expand_service.py -v`
- [ ] **Step 5:** Commit: `refactor(graph): extract shape_node for expand and resolve`

---

## Task 2: ENTRY_RESOLVERS registry (tasks §1)

- [ ] **Step 1:** Add `EntryResolver` to `codegraph_core/graph/types.py` (or `entry_resolvers.py`):

```python
@dataclass(frozen=True)
class EntryResolver:
    kind: str
    node_type: str
    match_column: str
```

- [ ] **Step 2:** Create `codegraph_core/graph/test_entry_resolvers.py` (RED):
  - `test_has_command_id_and_flow_id_resolvers`
  - `test_get_resolver_hit` / `test_get_resolver_miss`
  - `test_unknown_node_type_in_registry_raises`

- [ ] **Step 3:** Create `codegraph_core/graph/entry_resolvers.py` (GREEN):

```python
ENTRY_RESOLVERS: tuple[EntryResolver, ...] = (
    EntryResolver("commandId", "service_entry", "command_id"),
    EntryResolver("flowId", "flow", "flow_id"),
)

def get_resolver(kind: str) -> EntryResolver | None: ...
def _validate_entry_resolvers() -> None: ...  # node_type in NODE_SPECS
```

- [ ] **Step 4:** Call `_validate_entry_resolvers()` from `validation.py` or `graph/__init__.py`
- [ ] **Step 5:** Run: `pytest codegraph_core/graph/test_entry_resolvers.py -v`
- [ ] **Step 6:** Commit: `feat(resolve): add ENTRY_RESOLVERS registry`

---

## Task 3: resolve_service + validation (tasks §2–§5)

- [ ] **Step 1:** Create `codegraph_core/graph/resolve_validation.py`:

```python
def validate_resolve_input(schema: str, kind: str, value: str) -> None:
    SchemaValidator.validate(schema)
    if not value or not value.strip():
        raise ValueError("value must be non-empty")
    if get_resolver(kind) is None:
        raise ValueError(f"Unknown resolver kind: {kind}")
```

- [ ] **Step 2:** Create `codegraph_core/graph/resolve_service.py`:

```python
RESOLVE_MATCH_LIMIT = 50

@dataclass
class ResolveResult:
    status: str  # notFound | found | multiple
    roots: list[dict]
    candidates: list[dict]

def build_resolve_query(resolver: EntryResolver, limit: int) -> str: ...
def resolve_entry(schema, kind, value, q_fn=q) -> ResolveResult: ...
```

- [ ] **Step 3:** Create `codegraph_core/graph/test_resolve_validation.py` — unknown kind, empty value, bad schema
- [ ] **Step 4:** Create `codegraph_core/graph/test_resolve_service.py` (mock `q_fn`):
  - `test_command_id_found` — 1 row → status=found, roots[0].type=service_entry
  - `test_flow_id_found` — 1 row → type=flow
  - `test_not_found` — 0 rows → notFound, HTTP-neutral empty lists
  - `test_multiple` — 2 rows → multiple, candidates len=2, roots empty
  - `test_node_shape_expand_compatible` — roots[0] has only type+id needed for expand
  - `test_sql_injection_safe` — value in params not SQL string
  - `test_unknown_kind_raises_before_q`

- [ ] **Step 5:** Run: `pytest codegraph_core/graph/test_resolve*.py -v`
- [ ] **Step 6:** Export `resolve_entry` from `codegraph_core/graph/__init__.py`
- [ ] **Step 7:** Commit: `feat(resolve): add resolve_entry with three-state semantics`

---

## Task 4: HTTP route GET /api/v1/resolve (tasks §2.1)

- [ ] **Step 1:** Create `codegraph_server/schemas_resolve.py`:

```python
class GraphNodeOut(BaseModel):  # or reuse from schemas_expand
    type: str
    id: int
    title: str | None = None
    subtitle: str | None = None

class ResolveResponse(BaseModel):
    status: str
    roots: list[GraphNodeOut]
    candidates: list[GraphNodeOut]
```

- [ ] **Step 2:** Add to `codegraph_server/routes.py`:

```python
@router.get("/resolve", response_model=ResolveResponse)
def resolve(schema: str, kind: str, value: str):
    try:
        result = resolve_entry(schema, kind, value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ResolveResponse(
        status=result.status,
        roots=result.roots,
        candidates=result.candidates,
    )
```

- [ ] **Step 3:** Create `codegraph_server/test_resolve_route.py`:
  - Happy path 200 + JSON shape (mock resolve_entry)
  - Unknown kind → 422
  - Empty value → 422
  - notFound → 200 with empty roots

- [ ] **Step 4:** Run: `PYTHONPATH=. pytest codegraph_server/test_resolve_route.py codegraph_core/graph/test_resolve*.py -v`
- [ ] **Step 5:** Commit: `feat(resolve): add GET /api/v1/resolve endpoint`

---

## Task 5: Spec alignment & full suite (tasks §6)

- [ ] **Step 1:** Fix delta spec `specs/graph-api/spec.md`:
  - `service_entries` → `service_entry`, `flows` → `flow` in Scenario THEN clauses

- [ ] **Step 2:** Run full graph + resolve tests:

```bash
PYTHONPATH=. pytest codegraph_core/graph/ codegraph_server/test_resolve_route.py codegraph_server/test_expand_route.py -v --tb=short
```

- [ ] **Step 3:** Smoke (optional, needs MySQL):

```bash
curl "http://localhost:8000/api/v1/resolve?schema=YOUR_SCHEMA&kind=commandId&value=SomeCommand"
```

- [ ] **Step 4:** Mark all `tasks.md` checkboxes `[x]`
- [ ] **Step 5:** Commit: `docs(openspec): fix resolve spec nodeType names`

---

## Task 6: Pre-verify checklist

- [ ] **Step 1:** Confirm ENTRY_RESOLVERS has exactly commandId + flowId
- [ ] **Step 2:** Confirm resolve nodes match expand `GraphNode` shape (type, id, title, subtitle)
- [ ] **Step 3:** Grep — no hand-written resolve SQL outside `resolve_service.py`
- [ ] **Step 4:** All tasks §6 scenarios have matching tests

---

## Apply checklist mapping

| tasks.md section | Plan task |
|------------------|-----------|
| §1 注册表         | Task 2    |
| §2 端点与校验     | Task 3–4  |
| §3 解析执行       | Task 3    |
| §4 三态           | Task 3    |
| §5 防护           | Task 3–4  |
| §6 测试           | Tasks 2–5 |

After apply: `/opsx:verify` → commit → `/opsx:archive` (sync graph-api delta to main spec).
