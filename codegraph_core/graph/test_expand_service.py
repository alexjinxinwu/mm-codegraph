"""Tests for expand_service — hydrate and expand_neighbors."""

from unittest.mock import patch

import pytest

from codegraph_core.graph.expand_service import (
    EXPAND_NEIGHBOR_LIMIT,
    expand_neighbors,
    hydrate_node,
)


def test_hydrate_flow_includes_flow_id():
    calls = []

    def q_fn(schema, sql, params=()):
        calls.append((schema, sql, params))
        return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]

    row = hydrate_node("S", "flow", 10, q_fn=q_fn)
    assert row is not None
    assert "`flow_id`" in calls[0][1]
    assert calls[0][2] == (10,)


def test_hydrate_bridge_includes_before_beans():
    calls = []

    def q_fn(schema, sql, params=()):
        calls.append(sql)
        return [{"id": 2, "bridge_id": "B1", "logic_type": "x", "before_beans": "a,b"}]

    hydrate_node("S", "bridge", 2, q_fn=q_fn)
    assert "`before_beans`" in calls[0]


def test_hydrate_not_found():
    def q_fn(schema, sql, params=()):
        return []

    assert hydrate_node("S", "flow", 999, q_fn=q_fn) is None


def test_hydrate_uses_bound_params():
    captured = {}

    def q_fn(schema, sql, params=()):
        captured["sql"] = sql
        captured["params"] = params
        return [{"id": 1, "flow_id": "F", "flow_type": "t"}]

    hydrate_node("S", "flow", 42, q_fn=q_fn)
    assert "42" not in captured["sql"]
    assert captured["params"] == (42,)


def test_expand_not_found_empty():
    def q_fn(schema, sql, params=()):
        return []

    result = expand_neighbors("S", "flow", 999, edge_ids=["flow.states"], q_fn=q_fn)
    assert result.nodes == []
    assert result.edges == []


def test_expand_flow_states():
    def q_fn(schema, sql, params=()):
        if "FROM `flows`" in sql:
            return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]
        if "FROM `states`" in sql:
            return [{"id": 42, "state_name": "START", "flow_id": "F1"}]
        return []

    result = expand_neighbors("S", "flow", 10, edge_ids=["flow.states"], q_fn=q_fn)
    assert len(result.nodes) == 1
    assert result.nodes[0]["type"] == "state"
    assert result.nodes[0]["id"] == 42
    assert len(result.edges) == 1
    assert result.edges[0]["ruleId"] == "flow.states"


def test_expand_bean_java_class():
    def q_fn(schema, sql, params=()):
        if "FROM `beans`" in sql:
            return [{"id": 5, "bean_id": "b1", "bean_class": "com.foo.Bar"}]
        if "FROM `java_classes`" in sql:
            assert "`full_qualified_name` = %s" in sql
            assert params[0] == "com.foo.Bar"
            return [{"id": 7, "class_name": "Bar", "package_name": "com.foo"}]
        return []

    result = expand_neighbors(
        "S", "bean", 5, edge_ids=["bean.java_class"], q_fn=q_fn
    )
    assert result.nodes[0]["type"] == "java_class"
    assert result.nodes[0]["id"] == 7


def test_expand_state_activities():
    def q_fn(schema, sql, params=()):
        if "FROM `states`" in sql:
            return [
                {
                    "id": 7,
                    "state_name": "START",
                    "flow_id": "F1",
                }
            ]
        if "FROM `activities`" in sql:
            assert "`flow_id` = %s" in sql
            assert "`state_name` = %s" in sql
            return [{"id": 99, "activity_name": "act1", "activity_id": "A1"}]
        return []

    result = expand_neighbors(
        "S", "state", 7, edge_ids=["state.activities"], q_fn=q_fn
    )
    assert result.nodes[0]["type"] == "activity"


def test_expand_logic_activities():
    def q_fn(schema, sql, params=()):
        if "FROM `logics`" in sql:
            return [{"id": 3, "chain_id": "C1", "context_id": "ctx"}]
        if "FROM `activities`" in sql:
            assert "`logic` = %s" in sql
            assert params[0] == "C1"
            return [{"id": 11, "activity_name": "a", "activity_id": "x"}]
        return []

    result = expand_neighbors(
        "S", "logic", 3, edge_ids=["logic.activities"], q_fn=q_fn
    )
    assert result.nodes[0]["type"] == "activity"


def test_expand_bridge_beans_guard():
    def q_fn(schema, sql, params=()):
        if "FROM `bridges`" in sql:
            return [
                {
                    "id": 2,
                    "bridge_id": "B",
                    "logic_type": "t",
                    "before_beans": "b1,b2",
                }
            ]
        if "FROM `beans`" in sql:
            assert "`bean_id` IN (%s, %s)" in sql
            assert params[:2] == ("b1", "b2")
            return [
                {"id": 20, "bean_id": "b1", "bean_class": "c1"},
                {"id": 21, "bean_id": "b2", "bean_class": "c2"},
            ]
        return []

    result = expand_neighbors(
        "S", "bridge", 2, edge_ids=["bridge.beans"], q_fn=q_fn
    )
    assert len(result.nodes) == 2
    assert all(n["type"] == "bean" for n in result.nodes)


def test_expand_default_all_edges():
    sql_targets = []

    def q_fn(schema, sql, params=()):
        if "FROM `flows`" in sql:
            return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]
        sql_targets.append(sql)
        return []

    expand_neighbors("S", "flow", 10, edge_ids=None, q_fn=q_fn)
    # flow has 4 forward edges
    assert len(sql_targets) == 4


def test_expand_filtered_edge_ids():
    sql_targets = []

    def q_fn(schema, sql, params=()):
        if "FROM `flows`" in sql:
            return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]
        sql_targets.append(sql)
        return []

    expand_neighbors("S", "flow", 10, edge_ids=["flow.states"], q_fn=q_fn)
    assert len(sql_targets) == 1
    assert "FROM `states`" in sql_targets[0]


def test_expand_dedupe_nodes():
    def q_fn(schema, sql, params=()):
        if "FROM `flows`" in sql:
            return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]
        # same state row returned from two different edge queries
        if "FROM `states`" in sql:
            return [{"id": 42, "state_name": "S", "flow_id": "F1"}]
        if "FROM `activities`" in sql:
            return []
        if "FROM `transitions`" in sql:
            return []
        if "FROM `flow_tasks`" in sql:
            return []
        return []

    result = expand_neighbors("S", "flow", 10, edge_ids=["flow.states"], q_fn=q_fn)
    assert len(result.nodes) == 1


def test_expand_limit_passed_to_build_expand_query():
    captured_limits = []

    def q_fn(schema, sql, params=()):
        if "FROM `flows`" in sql:
            return [{"id": 10, "flow_id": "F1", "flow_type": "main"}]
        captured_limits.append(params[-1])
        return []

    expand_neighbors(
        "S", "flow", 10, edge_ids=["flow.states"], limit=50, q_fn=q_fn
    )
    assert captured_limits == [50]


def test_expand_sql_injection_safe():
    malicious = "'; DROP TABLE--"

    def q_fn(schema, sql, params=()):
        if "FROM `beans`" in sql:
            return [
                {
                    "id": 5,
                    "bean_id": "b",
                    "bean_class": malicious,
                }
            ]
        if "FROM `java_classes`" in sql:
            assert malicious not in sql
            assert params[0] == malicious
            return [{"id": 1, "class_name": "x", "package_name": "y"}]
        return []

    expand_neighbors("S", "bean", 5, edge_ids=["bean.java_class"], q_fn=q_fn)


def test_expand_unknown_type_raises_before_q():
    called = False

    def q_fn(*args, **kwargs):
        nonlocal called
        called = True
        return []

    with pytest.raises(ValueError, match="Unknown node type"):
        expand_neighbors("S", "bad_type", 1, q_fn=q_fn)
    assert not called


def test_expand_neighbor_limit_default():
    assert EXPAND_NEIGHBOR_LIMIT == 200
