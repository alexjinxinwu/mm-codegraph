"""Tests for EDGE_RULES registry."""

import pytest

from codegraph_core.graph.edge_rules import (
    EDGE_RULES,
    GUARD_EDGE_IDS,
    _validate_edge_rules,
    get_edge_rule,
    get_edges_from,
)
from codegraph_core.graph.node_specs import NODE_SPECS
from codegraph_core.graph.types import EdgeRule, RegistryError


def _rule_ids() -> set[str]:
    return {rule.id for rule in EDGE_RULES}


def test_reachable_chain_service_entry_to_java_method():
    assert "service_entry.bean" in _rule_ids()
    assert "bean.java_class" in _rule_ids()
    assert "java_class.java_methods" in _rule_ids()


def test_reachable_chain_flow_subtree():
    assert "flow.states" in _rule_ids()
    assert "state.activities" in _rule_ids()
    assert "activity.transitions" in _rule_ids()


def test_logic_subtree_with_guard():
    assert "logic.logic_steps" in _rule_ids()
    assert "logic.bridges" in _rule_ids()
    assert "bridge.beans" in _rule_ids()
    guard = get_edge_rule("bridge.beans")
    assert guard is not None
    assert guard.guard is not None


def test_semantic_edges():
    activities = get_edge_rule("logic.activities")
    flow_tasks = get_edge_rule("logic.flow_tasks")
    assert activities is not None
    assert flow_tasks is not None
    assert activities.match == (("chain_id", "logic"),)
    assert flow_tasks.match == (("chain_id", "logic"),)
    assert activities.assumption
    assert flow_tasks.assumption


def test_guard_edge_bridge_beans():
    rule = get_edge_rule("bridge.beans")
    assert rule is not None
    assert rule.match == (("before_beans", "bean_id"),)
    assert rule.guard is not None


def test_get_edges_from_flow():
    edges = get_edges_from("flow")
    assert len(edges) == 4
    assert {e.id for e in edges} == {
        "flow.states",
        "flow.flow_tasks",
        "flow.activities",
        "flow.transitions",
    }


def test_duplicate_rule_id_raises():
    duplicate = EDGE_RULES + (EDGE_RULES[0],)
    with pytest.raises(RegistryError, match="Duplicate"):
        _validate_edge_rules(NODE_SPECS, duplicate)


def test_unknown_from_type_raises():
    bad = (
        EdgeRule(
            "bad.edge",
            "nonexistent_type",
            "flow",
            "bad",
            (("flow_id", "flow_id"),),
        ),
    )
    with pytest.raises(RegistryError, match="unknown from_type"):
        _validate_edge_rules(NODE_SPECS, bad)


def test_guard_edge_missing_guard_raises():
    unguarded = EdgeRule(
        "bridge.beans",
        "bridge",
        "bean",
        "beans",
        (("before_beans", "bean_id"),),
        guard=None,
    )
    rules = tuple(r for r in EDGE_RULES if r.id != "bridge.beans") + (unguarded,)
    with pytest.raises(RegistryError, match="missing guard"):
        _validate_edge_rules(NODE_SPECS, rules)


def test_guard_edge_ids_cover_bridge_beans():
    assert "bridge.beans" in GUARD_EDGE_IDS
