"""Tests for NODE_SPECS registry."""

import pytest

from codegraph_core.graph.node_specs import (
    EXPECTED_NODE_TYPES,
    NODE_SPECS,
    _validate_node_specs,
    get_node_spec,
)
from codegraph_core.graph.types import NodeSpec, RegistryError


def test_flow_node_spec():
    spec = get_node_spec("flow")
    assert spec is not None
    assert spec.id_column == "id"
    assert spec.title == "flow_id"
    assert spec.subtitle == "flow_type"
    assert spec.table == "flows"


def test_all_fourteen_node_types():
    assert set(NODE_SPECS.keys()) == EXPECTED_NODE_TYPES
    assert len(NODE_SPECS) == 14


def test_get_node_spec_hit():
    assert get_node_spec("bean") is not None


def test_get_node_spec_miss():
    assert get_node_spec("unknown_type") is None


def test_invalid_registry_raises():
    bad = dict(NODE_SPECS)
    bad["flow"] = NodeSpec("flow", "", "id", "flow_id", "flow_type")
    with pytest.raises(RegistryError, match="missing table"):
        _validate_node_specs(bad)
