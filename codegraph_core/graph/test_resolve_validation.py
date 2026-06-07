"""Tests for resolve input validation."""

import pytest

from codegraph_core.graph.resolve_validation import validate_resolve_input


def test_invalid_schema_raises():
    with pytest.raises(ValueError, match="非法 schema"):
        validate_resolve_input("", "commandId", "C1")


def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="Unknown resolver kind"):
        validate_resolve_input("S", "unknown", "v")


def test_empty_value_raises():
    with pytest.raises(ValueError, match="non-empty"):
        validate_resolve_input("S", "commandId", "  ")


def test_valid_input_passes():
    validate_resolve_input("my_schema", "commandId", "Cmd1")
