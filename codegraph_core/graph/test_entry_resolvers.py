"""Tests for ENTRY_RESOLVERS registry."""

import codegraph_core.graph.entry_resolvers as entry_resolvers_mod
import pytest

from codegraph_core.graph.entry_resolvers import (
    ENTRY_RESOLVERS,
    _validate_entry_resolvers,
    get_resolver,
)
from codegraph_core.graph.node_specs import NODE_SPECS
from codegraph_core.graph.types import EntryResolver, RegistryError


def test_has_command_id_and_flow_id_resolvers():
    kinds = {r.kind for r in ENTRY_RESOLVERS}
    assert kinds >= {"commandId", "flowId"}


def test_get_resolver_hit():
    r = get_resolver("commandId")
    assert r is not None
    assert r.node_type == "service_entry"
    assert r.match_column == "command_id"


def test_get_resolver_miss():
    assert get_resolver("unknown") is None


def test_validate_catches_bad_node_type():
    original = entry_resolvers_mod.ENTRY_RESOLVERS
    try:
        entry_resolvers_mod.ENTRY_RESOLVERS = (
            EntryResolver("x", "bad_type", "col"),
        )
        with pytest.raises(RegistryError, match="unknown node_type"):
            _validate_entry_resolvers(NODE_SPECS)
    finally:
        entry_resolvers_mod.ENTRY_RESOLVERS = original


def test_validate_passes_for_builtin_resolvers():
    _validate_entry_resolvers(NODE_SPECS)
