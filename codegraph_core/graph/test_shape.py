"""Tests for shape_node."""

from codegraph_core.graph.shape import shape_node


def test_shape_flow_node():
    node = shape_node(
        "flow",
        {"id": 10, "flow_id": "F1", "flow_type": "main"},
    )
    assert node == {
        "type": "flow",
        "id": 10,
        "title": "F1",
        "subtitle": "main",
    }


def test_shape_service_entry_node():
    node = shape_node(
        "service_entry",
        {"id": 5, "name": "cmd", "entry_type": "command"},
    )
    assert node["type"] == "service_entry"
    assert node["id"] == 5
