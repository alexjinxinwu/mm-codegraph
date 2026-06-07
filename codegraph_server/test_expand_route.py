"""HTTP tests for POST /api/v1/expand."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from codegraph_core.graph.expand_service import ExpandResult
from codegraph_server.app import app

client = TestClient(app)


def test_expand_happy_path():
    mock_result = ExpandResult(
        nodes=[{"type": "state", "id": 42, "title": "START", "subtitle": "F1"}],
        edges=[
            {
                "ruleId": "flow.states",
                "from": {"type": "flow", "id": 10},
                "to": {"type": "state", "id": 42},
                "label": "states",
            }
        ],
    )
    with patch(
        "codegraph_server.routes.expand_neighbors", return_value=mock_result
    ) as mock_expand:
        resp = client.post(
            "/api/v1/expand",
            json={
                "schema": "my_schema",
                "node": {"type": "flow", "id": 10},
                "edgeIds": ["flow.states"],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"][0]["type"] == "state"
    assert data["edges"][0]["ruleId"] == "flow.states"
    assert data["edges"][0]["from"]["id"] == 10
    mock_expand.assert_called_once_with("my_schema", "flow", 10, ["flow.states"])


def test_expand_unknown_node_type_422():
    with patch(
        "codegraph_server.routes.expand_neighbors",
        side_effect=ValueError("Unknown node type: bad"),
    ) as mock_expand:
        resp = client.post(
            "/api/v1/expand",
            json={"schema": "S", "node": {"type": "bad", "id": 1}},
        )
    assert resp.status_code == 422
    mock_expand.assert_called_once()


def test_expand_invalid_edge_id_422():
    with patch(
        "codegraph_server.routes.expand_neighbors",
        side_effect=ValueError("Unknown edge rule: nope"),
    ):
        resp = client.post(
            "/api/v1/expand",
            json={
                "schema": "S",
                "node": {"type": "flow", "id": 1},
                "edgeIds": ["nope"],
            },
        )
    assert resp.status_code == 422


def test_expand_not_found_empty():
    with patch(
        "codegraph_server.routes.expand_neighbors",
        return_value=ExpandResult(nodes=[], edges=[]),
    ):
        resp = client.post(
            "/api/v1/expand",
            json={"schema": "S", "node": {"type": "flow", "id": 99999}},
        )
    assert resp.status_code == 200
    assert resp.json() == {"nodes": [], "edges": []}


def test_expand_invalid_node_id_422():
    resp = client.post(
        "/api/v1/expand",
        json={"schema": "S", "node": {"type": "flow", "id": 0}},
    )
    assert resp.status_code == 422
