"""FastAPI gateway routes. Orchestrates the pipeline over gRPC (spec sections 4.1 & 17).

The gateway holds no business logic — it builds protobuf requests, calls internal
gRPC services with explicit deadlines, maps responses back to Pydantic, and returns
JSON. gRPC status codes are translated into appropriate HTTP responses.
"""
from __future__ import annotations

import uuid

import grpc
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ..core.config import settings
from ..core.logging import new_request_id
from ..grpc_clients import clients, deadline
from ..grpc_gen import (
    ai_extraction_pb2,
    artifact_pb2,
    clarification_pb2,
    common_pb2,
    date_normalization_pb2,
    event_validation_pb2,
    ics_generation_pb2,
    input_processing_pb2,
    reminder_pb2,
)
from ..grpc_servers.mapping import (
    _ANCHOR_TO_PB,
    _UNIT_TO_PB,
    event_from_pb,
    event_to_pb,
)
from ..schemas.event import ValidationStatus
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClarificationsRequest,
    GenerateRequest,
    GenerateResponse,
    ReminderValidateRequest,
    ReminderValidateResponse,
    ValidateRequest,
    ValidateResponse,
)

router = APIRouter(prefix="/api/v1")


def _context(timezone: str = "UTC", locale: str = "en-US") -> common_pb2.RequestContext:
    return common_pb2.RequestContext(
        request_id=new_request_id(), default_timezone=timezone, locale=locale)


def _reminder_to_pb(rem):
    return common_pb2.Reminder(
        amount=rem.amount, unit=_UNIT_TO_PB[rem.unit], anchor=_ANCHOR_TO_PB[rem.anchor])


def _handle_grpc_error(exc: grpc.RpcError) -> HTTPException:
    code = exc.code()
    detail = exc.details() or "Internal service error."
    mapping = {
        grpc.StatusCode.INVALID_ARGUMENT: 400,
        grpc.StatusCode.NOT_FOUND: 404,
        grpc.StatusCode.DEADLINE_EXCEEDED: 504,
        grpc.StatusCode.UNAVAILABLE: 503,
    }
    return HTTPException(status_code=mapping.get(code, 500), detail=detail)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty.")
    if len(req.text) > settings.MAX_TEXT_CHARACTERS:
        raise HTTPException(status_code=413, detail="Input text too large.")

    ctx = _context(req.timezone, req.locale)
    try:
        # 1. Input processing
        proc = clients.input.ProcessText(
            input_processing_pb2.ProcessTextRequest(
                context=ctx, text=req.text, email_subject=req.email_subject or "",
                sender=req.sender or ""),
            timeout=deadline())
        normalized_text = proc.source.text

        # 2. Extraction (Qwen or mock)
        extracted = clients.extraction.ExtractEvents(
            ai_extraction_pb2.ExtractEventsRequest(context=ctx, text=normalized_text),
            timeout=deadline())

        # 3. Normalize
        normalized = clients.normalize.NormalizeEvents(
            date_normalization_pb2.NormalizeEventsRequest(context=ctx, events=extracted.events),
            timeout=deadline())

        # 4. Validate
        validated = clients.validation.ValidateEvents(
            event_validation_pb2.ValidateEventsRequest(context=ctx, events=normalized.events),
            timeout=deadline())

        # 5. Clarification questions
        questions_resp = clients.clarification.GenerateClarificationQuestions(
            clarification_pb2.GenerateQuestionsRequest(context=ctx, events=validated.events),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)

    events = [event_from_pb(e) for e in validated.events]
    counts = _summarize(events)
    return AnalyzeResponse(
        batch_id=uuid.uuid4().hex,
        events=events,
        questions=[{
            "id": q.id, "event_id": q.event_id, "field": q.field,
            "question": q.question, "suggested_answers": list(q.suggested_answers),
        } for q in questions_resp.questions],
        used_mock=extracted.used_mock,
        model=extracted.model,
        status="ok" if events else "no_events",
        **counts,
    )


@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest):
    ctx = _context()
    try:
        resp = clients.validation.ValidateEvents(
            event_validation_pb2.ValidateEventsRequest(
                context=ctx, events=[event_to_pb(e) for e in req.events]),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)
    return ValidateResponse(events=[event_from_pb(e) for e in resp.events])


@router.post("/clarifications", response_model=ValidateResponse)
def clarifications(req: ClarificationsRequest):
    ctx = _context()
    answers = [clarification_pb2.ClarificationAnswer(
        question_id=a.question_id, event_id=a.event_id, field=a.field, answer=a.answer)
        for a in req.answers]
    try:
        resp = clients.clarification.ApplyClarificationAnswers(
            clarification_pb2.ApplyAnswersRequest(
                context=ctx, events=[event_to_pb(e) for e in req.events], answers=answers),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)
    return ValidateResponse(events=[event_from_pb(e) for e in resp.events])


@router.post("/reminders/validate", response_model=ReminderValidateResponse)
def reminders_validate(req: ReminderValidateRequest):
    ctx = _context()
    try:
        resp = clients.reminder.ValidateReminderSettings(
            reminder_pb2.ValidateReminderSettingsRequest(
                context=ctx, reminders=[_reminder_to_pb(r) for r in req.reminders]),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)
    from ..grpc_servers.mapping import _UNIT_FROM_PB, _ANCHOR_FROM_PB
    from ..schemas.event import Reminder, ReminderUnit, ReminderAnchor
    normalized = [Reminder(amount=n.amount,
                           unit=_UNIT_FROM_PB.get(n.unit, ReminderUnit.MINUTES),
                           anchor=_ANCHOR_FROM_PB.get(n.anchor, ReminderAnchor.START))
                  for n in resp.normalized]
    issues = [{"field": i.field, "code": i.code, "message": i.message,
               "blocks_export": i.blocks_export} for i in resp.issues]
    return ReminderValidateResponse(valid=resp.valid, normalized=normalized, issues=issues)


@router.post("/calendar/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    ctx = _context()
    try:
        # Apply reminder defaults
        with_reminders = clients.reminder.BuildReminderSpecifications(
            reminder_pb2.BuildReminderSpecsRequest(
                context=ctx, events=[event_to_pb(e) for e in req.events],
                default_reminders=[_reminder_to_pb(r) for r in req.default_reminders]),
            timeout=deadline())

        # Re-validate; block generation on errors.
        validated = clients.validation.ValidateEvents(
            event_validation_pb2.ValidateEventsRequest(context=ctx, events=with_reminders.events),
            timeout=deadline())
        events = [event_from_pb(e) for e in validated.events]
        blocking = [e for e in events if e.blocking_issues]
        if blocking:
            titles = ", ".join(e.title or "untitled" for e in blocking)
            raise HTTPException(status_code=422,
                                detail=f"Cannot generate: events have blocking errors ({titles}).")

        # Generate ICS
        gen = clients.ics.GenerateCalendar(
            ics_generation_pb2.GenerateCalendarRequest(
                context=ctx, events=validated.events, calendar_name=req.calendar_name),
            timeout=deadline())

        # Validate ICS semantically
        icsval = clients.ics_validation.ValidateCalendar(
            ics_generation_pb2.ValidateCalendarRequest(
                context=ctx, ics_content=gen.ics_content, expected_events=validated.events),
            timeout=deadline())
        if not icsval.valid:
            issues = [{"field": i.field, "code": i.code, "message": i.message} for i in icsval.issues]
            raise HTTPException(status_code=500,
                                detail={"message": "Generated ICS failed validation.", "issues": issues})

        # Store artifact
        from datetime import date
        filename = f"calendar_events_{date.today().isoformat()}.ics"
        art = clients.artifact.CreateArtifact(
            artifact_pb2.CreateArtifactRequest(
                context=ctx, content=gen.ics_content,
                content_type=gen.content_type, suggested_filename=filename),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)

    return GenerateResponse(
        artifact_id=art.artifact.artifact_id,
        filename=art.artifact.filename,
        event_count=gen.event_count,
        ics_valid=icsval.valid,
        validation_issues=[{"field": i.field, "code": i.code, "message": i.message}
                           for i in icsval.issues],
    )


@router.get("/calendar/download/{artifact_id}")
def download(artifact_id: str):
    ctx = _context()
    try:
        resp = clients.artifact.GetArtifact(
            artifact_pb2.GetArtifactRequest(context=ctx, artifact_id=artifact_id),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)
    return Response(
        content=resp.content,
        media_type=resp.artifact.content_type or "text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{resp.artifact.filename}"'},
    )


@router.post("/documents")
async def documents(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")
    ctx = _context()
    try:
        proc = clients.input.ProcessUploadedFile(
            input_processing_pb2.ProcessUploadedFileRequest(
                context=ctx, filename=file.filename or "upload", content=content),
            timeout=deadline())
    except grpc.RpcError as exc:
        raise _handle_grpc_error(exc)
    return {"text": proc.source.text, "character_count": proc.source.character_count}


def _summarize(events) -> dict:
    valid = sum(1 for e in events if e.validation_status == ValidationStatus.VALID)
    warn = sum(1 for e in events if e.validation_status == ValidationStatus.VALID_WITH_WARNINGS)
    clarify = sum(1 for e in events if e.validation_status == ValidationStatus.REQUIRES_CLARIFICATION)
    return {
        "total_events": len(events),
        "valid_events": valid,
        "events_with_warnings": warn,
        "events_requiring_clarification": clarify,
    }
