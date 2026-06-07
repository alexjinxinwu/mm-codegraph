# Graph Model & Forward Rules Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> to implement this plan task-by-task.

**Goal:** Add a declarative graph kernel in `codegraph_core/graph/` — 14 NodeSpecs, 19 forward EdgeRules, and `build_expand_query()` — so resolve/expand endpoints can share one SQL generation source.

**Architecture:** Static frozen dataclass registries (`NODE_SPECS`, `EDGE_RULES`) validated at import time. `build_expand_query(rule, node, limit)` returns `(sql, params)` for PyMySQL; callers execute via existing `QueryEngine.q()`. No HTTP/MCP changes in this change.

**Tech Stack:** Python 3, pytest, PyMySQL-style `%s` placeholders, dataclasses

**Spec refs:** `openspec/changes/add-graph-model-and-forward-rules/specs/graph-core/spec.md`

---

## Task 1: Scaffold `codegraph_core/graph/` package

- [ ] **Step 1:** Create directory `codegraph_core/graph/` with empty `__init__.py`
- [ ] **Step 2:** Create `codegraph_core/graph/types.py` with shared exception and dataclasses:

```python
class RegistryError(Exception):
    """Raised when NODE_SPECS or EDGE_RULES fail validation."""

@dataclass(frozen=True)
class NodeSpec:
    node_type: str
    table: str
    id_column: str
    title: str
    subtitle: str

@dataclass(frozen=True)
class EdgeRule:
    id: str
    from_type: str
    to_type: str
    label: str
    match: tuple[tuple[str, str], ...]
    direction: str = "out"
    guard: str | None = None
    assumption: str | None = None
```

- [ ] **Step 3:** Verify import works: `python -c "from codegraph_core.graph.types import NodeSpec, EdgeRule, RegistryError"`
- [ ] **Step 4:** Commit: `feat(graph): scaffold codegraph_core/graph package and types`

---

## Task 2: NodeSpec registry (tasks §1)

- [ ] **Step 1:** Create `codegraph_core/graph/test_node_specs.py` with failing tests (RED):
  - `test_flow_node_spec` — flow: id_column=`"id"`, title=`flow_id`, subtitle=`flow_type`, table=`flows`
  - `test_all_fourteen_node_types` — exactly 14 keys in registry
  - `test_get_node_spec_hit` — known type returns NodeSpec
  - `test_get_node_spec_miss` — unknown type returns `None`
  - `test_invalid_registry_raises` — (defer to Step 4 helper test)

- [ ] **Step 2:** Run tests, confirm RED:

```bash
cd /Users/alex.wu/WuDevSpace/yesclaw/mm-codegraph
pip install pytest
pytest codegraph_core/graph/test_node_specs.py -v
```

- [ ] **Step 3:** Create `codegraph_core/graph/node_specs.py` (GREEN):
  - Define `EXPECTED_NODE_TYPES` frozenset of 14 type names
  - Build `NODE_SPECS: dict[str, NodeSpec]` from tasks.md §1.2 table
  - Implement `get_node_spec(node_type: str) -> NodeSpec | None`
  - Implement `_validate_node_specs()` — 14 types present, id_column/table non-empty

- [ ] **Step 4:** Add test for validation helper — temporarily patch registry in test to omit `table`, assert `RegistryError`
- [ ] **Step 5:** Run tests, confirm GREEN: `pytest codegraph_core/graph/test_node_specs.py -v`
- [ ] **Step 6:** Commit: `feat(graph): add NODE_SPECS registry with 14 node types`

---

## Task 3: EdgeRule registry (tasks §2)

- [ ] **Step 1:** Create `codegraph_core/graph/test_edge_rules.py` with failing tests (RED):
  - `test_reachable_chain_service_entry_to_java_method` — edges exist: service_entry→bean, bean→java_class, java_class→java_method
  - `test_reachable_chain_flow_subtree` — flow→state, state→activity, activity→transition
  - `test_logic_subtree_with_guard` — logic→logic_step, logic→bridge, bridge→bean (guard)
  - `test_semantic_edges` — logic.activities / logic.flow_tasks: match=`chain_id→logic`, assumption non-empty
  - `test_guard_edge_bridge_beans` — bridge.beans: match=`before_beans→bean_id`, guard non-empty
  - `test_get_edges_from_flow` — returns all edges where from_type=`flow` (4 edges)
  - `test_duplicate_rule_id_raises` — validation catches duplicate ids
  - `test_unknown_from_type_raises` — validation catches bad from/to
  - `test_guard_edge_missing_guard_raises` — guard category without guard field fails

- [ ] **Step 2:** Run tests, confirm RED: `pytest codegraph_core/graph/test_edge_rules.py -v`

- [ ] **Step 3:** Create `codegraph_core/graph/edge_rules.py` (GREEN):
  - Build `EDGE_RULES: tuple[EdgeRule, ...]` with all 19 rules from tasks.md §2.2–2.5
  - Labels: use readable defaults e.g. `"flow"`, `"bean"`, or match id suffix
  - Semantic edges: set `assumption` per tasks table
  - Guard edge: `guard="split_comma"` (or descriptive string)
  - Implement `get_edge_rule(rule_id: str) -> EdgeRule | None`
  - Implement `get_edges_from(from_type: str) -> list[EdgeRule]`
  - Implement `_validate_edge_rules(node_specs: dict)` — from/to exist, ids unique, guard present when guard edge

- [ ] **Step 4:** Run tests, confirm GREEN: `pytest codegraph_core/graph/test_edge_rules.py -v`
- [ ] **Step 5:** Commit: `feat(graph): add EDGE_RULES registry with 19 forward edges`

---

## Task 4: Wire import-time validation (design §5)

- [ ] **Step 1:** Create `codegraph_core/graph/validation.py`:

```python
def validate_registries() -> None:
    _validate_node_specs()
    _validate_edge_rules(NODE_SPECS)
```

- [ ] **Step 2:** Update `codegraph_core/graph/__init__.py` to import registries and call `validate_registries()` at module load
- [ ] **Step 3:** Export public API:

```python
from codegraph_core.graph.node_specs import get_node_spec, NODE_SPECS
from codegraph_core.graph.edge_rules import get_edge_rule, get_edges_from, EDGE_RULES
from codegraph_core.graph.expand_query import build_expand_query  # added in Task 5
```

- [ ] **Step 4:** Add test `test_import_triggers_validation` — `import codegraph_core.graph` succeeds without error
- [ ] **Step 5:** Run all graph tests: `pytest codegraph_core/graph/ -v`
- [ ] **Step 6:** Commit: `feat(graph): wire import-time registry validation`

---

## Task 5: `build_expand_query` generator (tasks §3)

- [ ] **Step 1:** Create `codegraph_core/graph/test_expand_query.py` with failing tests (RED):
  - `test_bean_java_class_aliased_column` — rule `bean.java_class`, node `{"bean_class": "com.foo.Bar"}`, SQL contains `` `full_qualified_name` = %s ``, params=`("com.foo.Bar", limit)`
  - `test_state_activities_composite_key` — rule `state.activities`, WHERE has both `flow_id` and `state_name`
  - `test_logic_activities_semantic` — rule `logic.activities`, WHERE `` `logic` = %s ``, param is chain_id value
  - `test_bridge_beans_guard_multi` — before_beans=`"b1,b2"`, WHERE `` `bean_id` IN (%s, %s) ``, params=`("b1", "b2", limit)`
  - `test_bridge_beans_guard_single` — before_beans=`"b1"`, IN with one placeholder
  - `test_bridge_beans_guard_empty` — before_beans=`""`, SQL contains `WHERE 1=0`
  - `test_limit_clause` — SQL ends with `LIMIT %s`, last param is limit int
  - `test_sql_injection_safe` — node value `"'; DROP TABLE--"`, value in params tuple not inlined in SQL string
  - `test_select_columns` — SELECT includes target NodeSpec id_column, title, subtitle

- [ ] **Step 2:** Run tests, confirm RED: `pytest codegraph_core/graph/test_expand_query.py -v`

- [ ] **Step 3:** Create `codegraph_core/graph/expand_query.py` (GREEN):

```python
def build_expand_query(rule: EdgeRule, node: dict, limit: int) -> tuple[str, tuple]:
    to_spec = get_node_spec(rule.to_type)
    if to_spec is None:
        raise ValueError(f"Unknown to_type: {rule.to_type}")
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a non-negative int")

    cols = f"`{to_spec.id_column}`, `{to_spec.title}`, `{to_spec.subtitle}`"
    table = f"`{to_spec.table}`"

    if rule.guard is not None:
        src_col, dst_col = rule.match[0]
        raw = node.get(src_col, "") or ""
        values = [v.strip() for v in str(raw).split(",") if v.strip()]
        if not values:
            sql = f"SELECT {cols} FROM {table} WHERE 1=0 LIMIT %s"
            return sql, (limit,)
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"SELECT {cols} FROM {table} WHERE `{dst_col}` IN ({placeholders}) LIMIT %s"
        return sql, (*values, limit)

    clauses = []
    params: list = []
    for src_col, dst_col in rule.match:
        clauses.append(f"`{dst_col}` = %s")
        params.append(node[src_col])
    where = " AND ".join(clauses)
    sql = f"SELECT {cols} FROM {table} WHERE {where} LIMIT %s"
    return sql, (*params, limit)
```

- [ ] **Step 4:** Run tests, confirm GREEN: `pytest codegraph_core/graph/test_expand_query.py -v`
- [ ] **Step 5:** Commit: `feat(graph): add build_expand_query SQL generator`

---

## Task 6: Package exports & full test suite (tasks §4)

- [ ] **Step 1:** Update `codegraph_core/__init__.py` to re-export graph public API (optional but recommended):

```python
from codegraph_core.graph import (
    build_expand_query,
    get_node_spec,
    get_edges_from,
    get_edge_rule,
    NODE_SPECS,
    EDGE_RULES,
)
```

- [ ] **Step 2:** Run full graph test suite:

```bash
pytest codegraph_core/graph/ -v
```

- [ ] **Step 3:** Run existing MCP tests to confirm no regression:

```bash
pytest codegraph_mcp/test_search_service_impact.py -v -k "not integration" 2>/dev/null || \
pytest codegraph_mcp/test_search_service_impact.py -v
```

- [ ] **Step 4:** Manual smoke — no DB required:

```bash
python -c "
from codegraph_core.graph import get_edges_from, build_expand_query
rules = get_edges_from('bean')
r = next(x for x in rules if x.id == 'bean.java_class')
sql, params = build_expand_query(r, {'bean_class': 'com.example.Foo'}, 50)
print(sql)
print(params)
"
```

- [ ] **Step 5:** Update `tasks.md` checkboxes as each section completes during apply
- [ ] **Step 6:** Commit: `feat(graph): export graph kernel from codegraph_core`

---

## Task 7: Final verification before verify artifact

- [ ] **Step 1:** Confirm all 19 EDGE_RULES ids match tasks.md §2.2–2.5 exactly
- [ ] **Step 2:** Confirm all 14 NODE_SPECS match tasks.md §1.2 table exactly
- [ ] **Step 3:** Grep for hardcoded expand SQL outside `graph/` — should find none (this change adds kernel only)
- [ ] **Step 4:** Run `pytest codegraph_core/graph/ -v --tb=short` — all green
- [ ] **Step 5:** Commit if any docstring/fixture tweaks remain

---

## Apply checklist mapping

| tasks.md section | Plan task |
|------------------|-----------|
| §1 NodeSpec      | Task 2    |
| §2 EDGE_RULES    | Task 3–4  |
| §3 build_expand_query | Task 5 |
| §4 Tests         | Tasks 2–6 |

After apply completes, run `/opsx:verify` or `openspec-continue-change` to produce `verify.md`.
