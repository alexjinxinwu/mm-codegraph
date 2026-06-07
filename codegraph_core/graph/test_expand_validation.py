"""Tests for expand input validation."""

import pytest

from codegraph_core.graph.expand_validation import validate_expand_input


def test_invalid_schema_raises():
    with pytest.raises(ValueError, match="非法 schema"):
        validate_expand_input("", "flow", 1, None)


def test_unknown_node_type_raises():
    with pytest.raises(ValueError, match="Unknown node type"):
        validate_expand_input("my_schema", "unknown_type", 1, None)


def test_unknown_edge_id_raises():
    with pytest.raises(ValueError, match="Unknown edge rule"):
        validate_expand_input("my_schema", "flow", 1, ["not.a.rule"])


def test_edge_id_from_mismatch_raises():
    with pytest.raises(ValueError, match="not applicable"):
        validate_expand_input("my_schema", "flow", 1, ["bean.java_class"])


def test_valid_input_passes():
    validate_expand_input("my_schema", "flow", 10, ["flow.states"])
    validate_expand_input("my_schema", "flow", 10, None)
