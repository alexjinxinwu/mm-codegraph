"""HTTP tests for GET /api/v1/resolve."""

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from codegraph_core.graph.resolve_service import ResolveResult
from codegraph_server.app import app

client = TestClient(app)


def test_resolve_happy_path():
    mock = ResolveResult(
        status="found",
        roots=[{"type": "service_entry", "id": 1, "title": "n", "subtitle": "t"}],
        candidates=[],
    )
    with patch("codegraph_server.routes.resolve_entry", return_value=mock) as m:
        resp = client.get(
            "/api/v1/resolve",
            params={"schema": "S", "kind": "commandId", "value": "Cmd1"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "found"
    assert data["roots"][0]["type"] == "service_entry"
    m.assert_called_once_with("S", "commandId", "Cmd1")


def test_resolve_unknown_kind_422():
    with patch(
        "codegraph_server.routes.resolve_entry",
        side_effect=ValueError("Unknown resolver kind: bad"),
    ):
        resp = client.get(
            "/api/v1/resolve",
            params={"schema": "S", "kind": "bad", "value": "x"},
        )
    assert resp.status_code == 422


def test_resolve_empty_value_422():
    resp = client.get(
        "/api/v1/resolve",
        params={"schema": "S", "kind": "commandId", "value": ""},
    )
    assert resp.status_code == 422


def test_resolve_not_found_200():
    mock = ResolveResult(status="notFound", roots=[], candidates=[])
    with patch("codegraph_server.routes.resolve_entry", return_value=mock):
        resp = client.get(
            "/api/v1/resolve",
            params={"schema": "S", "kind": "commandId", "value": "Missing"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "notFound"
    assert resp.json()["roots"] == []
