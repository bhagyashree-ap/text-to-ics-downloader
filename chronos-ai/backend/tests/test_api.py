"""HTTP API tests via FastAPI TestClient (spec section 17 & 22).

Requires generated stubs + a running in-process gRPC server. We start the gRPC
server in a fixture and point the gateway's client targets at it.
"""
from __future__ import annotations

import pytest

pytest.importorskip("grpc")
pytest.importorskip("httpx")
pytest.importorskip("app.grpc_gen.common_pb2", reason="Run scripts/gen_proto.py first.")

from concurrent import futures  # noqa: E402

import grpc  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    from app.grpc_servers import server as grpc_server_mod
    from app.core.config import settings

    server = grpc_server_mod.build_server()
    port = server.add_insecure_port("localhost:0")
    server.start()
    target = f"localhost:{port}"

    # Point every gateway client target at this ephemeral server.
    for attr in (
        "GRPC_INPUT_PROCESSING_TARGET", "GRPC_AI_EXTRACTION_TARGET",
        "GRPC_DATE_NORMALIZATION_TARGET", "GRPC_EVENT_VALIDATION_TARGET",
        "GRPC_CLARIFICATION_TARGET", "GRPC_REMINDER_TARGET",
        "GRPC_ICS_GENERATION_TARGET", "GRPC_ARTIFACT_TARGET",
    ):
        monkeypatch.setattr(settings, attr, target)

    # Reset cached channels so new targets take effect.
    from app.grpc_clients import client as client_mod
    client_mod._channel.cache_clear()

    from app.main import app
    with TestClient(app) as c:
        yield c
    server.stop(0)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["mock_mode"] is True


def test_analyze_and_generate_and_download(client):
    r = client.post("/api/v1/analyze", json={
        "text": "Team meeting October 20, 2026 from 2 PM to 3 PM.",
        "timezone": "America/New_York",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_events"] == 1
    assert data["used_mock"] is True
    events = data["events"]

    g = client.post("/api/v1/calendar/generate", json={
        "events": events,
        "default_reminders": [{"amount": 10, "unit": "MINUTES", "anchor": "START"}],
        "calendar_name": "My Events",
    })
    assert g.status_code == 200, g.text
    gen = g.json()
    assert gen["ics_valid"] is True
    assert gen["event_count"] == 1

    d = client.get(f"/api/v1/calendar/download/{gen['artifact_id']}")
    assert d.status_code == 200
    assert d.headers["content-type"].startswith("text/calendar")
    assert d.content.startswith(b"BEGIN:VCALENDAR")
    assert b"BEGIN:VALARM" in d.content


def test_empty_input_returns_400(client):
    r = client.post("/api/v1/analyze", json={"text": "   "})
    assert r.status_code == 400


def test_download_unknown_artifact_404(client):
    r = client.get("/api/v1/calendar/download/" + "0" * 32)
    assert r.status_code == 404
