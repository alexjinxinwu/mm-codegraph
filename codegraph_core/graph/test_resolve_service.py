"""Tests for resolve_entry service."""

import pytest

from codegraph_core.graph.resolve_service import resolve_entry


def test_command_id_found():
    def q_fn(schema, sql, params=()):
        assert "`command_id` = %s" in sql
        assert params[0] == "Cmd1"
        return [{"id": 12, "name": "MyCmd", "entry_type": "command"}]

    result = resolve_entry("S", "commandId", "Cmd1", q_fn=q_fn)
    assert result.status == "found"
    assert len(result.roots) == 1
    assert result.roots[0]["type"] == "service_entry"
    assert result.roots[0]["id"] == 12
    assert result.candidates == []


def test_flow_id_found():
    def q_fn(schema, sql, params=()):
        return [{"id": 3, "flow_id": "F1", "flow_type": "main"}]

    result = resolve_entry("S", "flowId", "F1", q_fn=q_fn)
    assert result.status == "found"
    assert result.roots[0]["type"] == "flow"


def test_not_found():
    def q_fn(schema, sql, params=()):
        return []

    result = resolve_entry("S", "commandId", "Missing", q_fn=q_fn)
    assert result.status == "notFound"
    assert result.roots == []
    assert result.candidates == []


def test_multiple():
    def q_fn(schema, sql, params=()):
        return [
            {"id": 1, "flow_id": "F1", "flow_type": "a"},
            {"id": 2, "flow_id": "F1", "flow_type": "b"},
        ]

    result = resolve_entry("S", "flowId", "F1", q_fn=q_fn)
    assert result.status == "multiple"
    assert result.roots == []
    assert len(result.candidates) == 2


def test_node_shape_expand_compatible():
    def q_fn(schema, sql, params=()):
        return [{"id": 7, "name": "n", "entry_type": "t"}]

    result = resolve_entry("S", "commandId", "C", q_fn=q_fn)
    node = result.roots[0]
    assert "type" in node and "id" in node
    assert set(node.keys()) >= {"type", "id", "title", "subtitle"}


def test_sql_injection_safe():
    malicious = "'; DROP--"

    def q_fn(schema, sql, params=()):
        assert malicious not in sql
        assert params[0] == malicious
        return []

    resolve_entry("S", "commandId", malicious, q_fn=q_fn)


def test_unknown_kind_raises_before_q():
    called = False

    def q_fn(*args, **kwargs):
        nonlocal called
        called = True
        return []

    with pytest.raises(ValueError, match="Unknown resolver kind"):
        resolve_entry("S", "bad_kind", "v", q_fn=q_fn)
    assert not called
