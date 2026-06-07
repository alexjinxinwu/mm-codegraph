"""Tests for build_expand_query SQL generator."""

from codegraph_core.graph.edge_rules import get_edge_rule
from codegraph_core.graph.expand_query import build_expand_query


def test_bean_java_class_aliased_column():
    rule = get_edge_rule("bean.java_class")
    sql, params = build_expand_query(rule, {"bean_class": "com.foo.Bar"}, 50)
    assert "`full_qualified_name` = %s" in sql
    assert params == ("com.foo.Bar", 50)
    assert "`java_classes`" in sql


def test_state_activities_composite_key():
    rule = get_edge_rule("state.activities")
    sql, params = build_expand_query(
        rule,
        {"flow_id": "F1", "state_name": "START"},
        100,
    )
    assert "`flow_id` = %s" in sql
    assert "`state_name` = %s" in sql
    assert " AND " in sql
    assert params == ("F1", "START", 100)


def test_logic_activities_semantic():
    rule = get_edge_rule("logic.activities")
    sql, params = build_expand_query(rule, {"chain_id": "CHAIN-1"}, 200)
    assert "`logic` = %s" in sql
    assert params == ("CHAIN-1", 200)


def test_bridge_beans_guard_multi():
    rule = get_edge_rule("bridge.beans")
    sql, params = build_expand_query(rule, {"before_beans": "b1,b2"}, 10)
    assert "`bean_id` IN (%s, %s)" in sql
    assert params == ("b1", "b2", 10)


def test_bridge_beans_guard_single():
    rule = get_edge_rule("bridge.beans")
    sql, params = build_expand_query(rule, {"before_beans": "b1"}, 10)
    assert "`bean_id` IN (%s)" in sql
    assert params == ("b1", 10)


def test_bridge_beans_guard_empty():
    rule = get_edge_rule("bridge.beans")
    sql, params = build_expand_query(rule, {"before_beans": ""}, 10)
    assert "WHERE 1=0" in sql
    assert params == (10,)


def test_limit_clause():
    rule = get_edge_rule("bean.java_class")
    sql, params = build_expand_query(rule, {"bean_class": "x"}, 42)
    assert sql.endswith("LIMIT %s")
    assert params[-1] == 42


def test_sql_injection_safe():
    rule = get_edge_rule("bean.java_class")
    malicious = "'; DROP TABLE--"
    sql, params = build_expand_query(rule, {"bean_class": malicious}, 50)
    assert malicious not in sql
    assert params[0] == malicious


def test_select_columns():
    rule = get_edge_rule("bean.java_class")
    sql, _ = build_expand_query(rule, {"bean_class": "com.foo.Bar"}, 50)
    assert "`id`" in sql
    assert "`class_name`" in sql
    assert "`package_name`" in sql
