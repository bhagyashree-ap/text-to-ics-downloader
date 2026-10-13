"""gRPC transport tests (spec section 22, cases 29-31 + serialization).

These require generated stubs (run `python scripts/gen_proto.py` first). They spin
up the in-process gRPC server on an ephemeral port and exercise it via a real client,
proving the proto round-trip and gRPC error handling.
"""
from __future__ import annotations

import pytest

grpc = pytest.importorskip("grpc")
pytest.importorskip("app.grpc_gen.common_pb2", reason="Run scripts/gen_proto.py first.")

from concurrent import futures  # noqa: E402

from app.grpc_gen import (  # noqa: E402
    ai_extraction_pb2,
    ai_extraction_pb2_grpc,
    common_pb2,
    ics_generation_pb2,
    ics_generation_pb2_grpc,
)
from app.grpc_servers import servicers  # noqa: E402


@pytest.fixture
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ai_extraction_pb2_grpc.add_AIExtractionServiceServicer_to_server(
        servicers.AIExtractionServicer(), server)
    ics_generation_pb2_grpc.add_ICSGenerationServiceServicer_to_server(
        servicers.ICSGenerationServicer(), server)
    ics_generation_pb2_grpc.add_ICSValidationServiceServicer_to_server(
        servicers.ICSValidationServicer(), server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    yield f"localhost:{port}"
    server.stop(0)


def test_extract_over_grpc(grpc_server):
    channel = grpc.insecure_channel(grpc_server)
    stub = ai_extraction_pb2_grpc.AIExtractionServiceStub(channel)
    ctx = common_pb2.RequestContext(request_id="t1", default_timezone="UTC")
    resp = stub.ExtractEvents(
        ai_extraction_pb2.ExtractEventsRequest(
            context=ctx, text="Meeting October 20, 2026 at 2 PM."),
        timeout=10)
    assert resp.used_mock is True
    assert len(resp.events) == 1
    assert resp.events[0].title


def test_generate_and_validate_over_grpc(grpc_server):
    channel = grpc.insecure_channel(grpc_server)
    extract = ai_extraction_pb2_grpc.AIExtractionServiceStub(channel)
    gen = ics_generation_pb2_grpc.ICSGenerationServiceStub(channel)
    val = ics_generation_pb2_grpc.ICSValidationServiceStub(channel)
    ctx = common_pb2.RequestContext(request_id="t2", default_timezone="UTC")

    ex = extract.ExtractEvents(
        ai_extraction_pb2.ExtractEventsRequest(
            context=ctx, text="Exam on November 5, 2026 from 9 AM to 11 AM."),
        timeout=10)
    g = gen.GenerateCalendar(
        ics_generation_pb2.GenerateCalendarRequest(context=ctx, events=ex.events, calendar_name="T"),
        timeout=10)
    assert g.ics_content.startswith(b"BEGIN:VCALENDAR")
    v = val.ValidateCalendar(
        ics_generation_pb2.ValidateCalendarRequest(
            context=ctx, ics_content=g.ics_content, expected_events=ex.events),
        timeout=10)
    assert v.valid is True


def test_deadline_exceeded(grpc_server):
    channel = grpc.insecure_channel(grpc_server)
    stub = ai_extraction_pb2_grpc.AIExtractionServiceStub(channel)
    ctx = common_pb2.RequestContext(request_id="t3", default_timezone="UTC")
    with pytest.raises(grpc.RpcError) as exc_info:
        stub.ExtractEvents(
            ai_extraction_pb2.ExtractEventsRequest(context=ctx, text="x" * 100),
            timeout=0.000001)  # impossibly short deadline
    assert exc_info.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
