"""Import-time validation smoke test."""


def test_import_triggers_validation():
    import importlib

    import codegraph_core.graph as graph

    importlib.reload(graph)
    assert graph.NODE_SPECS
    assert graph.EDGE_RULES
