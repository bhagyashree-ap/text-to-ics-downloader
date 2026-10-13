"""gRPC servicer implementations. Each wraps the shared deterministic service logic
and maps protobuf <-> CanonicalEvent. Requires generated stubs.
"""
from __future__ import annotations

import grpc

from ..core.logging import operation, set_request_id
from ..grpc_gen import (
    ai_extraction_pb2,
    ai_extraction_pb2_grpc,
    artifact_pb2,
    artifact_pb2_grpc,
    clarification_pb2,
    clarification_pb2_grpc,
    date_normalization_pb2,
    date_normalization_pb2_grpc,
    event_validation_pb2,
    event_validation_pb2_grpc,
    ics_generation_pb2,
    ics_generation_pb2_grpc,
    input_processing_pb2,
    input_processing_pb2_grpc,
    reminder_pb2,
    reminder_pb2_grpc,
)
from ..services import (
    artifact_service,
    clarification,
    date_normalizer,
    event_validation,
    ics_generator,
    ics_validation,
    input_processing,
    qwen_extraction,
    reminder_service,
)
from .mapping import event_from_pb, event_to_pb


def _ctx(context_msg):
    set_request_id(getattr(context_msg, "request_id", "") or "-")
    return context_msg


class InputProcessingServicer(input_processing_pb2_grpc.InputProcessingServiceServicer):
    def ProcessText(self, request, context):
        _ctx(request.context)
        with operation("input", "ProcessText"):
            try:
                text, truncated = input_processing.process_text(
                    request.text, request.email_subject, request.sender)
            except input_processing.InputError as exc:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            src = input_processing_pb2.NormalizedSource(
                text=text, source_type=request.source_type, email_subject=request.email_subject,
                sender=request.sender, character_count=len(text), truncated=truncated)
            return input_processing_pb2.ProcessResponse(source=src)

    def ProcessUploadedFile(self, request, context):
        _ctx(request.context)
        with operation("input", "ProcessUploadedFile"):
            try:
                text, truncated = input_processing.process_file(
                    request.filename, request.content)
            except input_processing.InputError as exc:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            src = input_processing_pb2.NormalizedSource(
                text=text, character_count=len(text), truncated=truncated)
            return input_processing_pb2.ProcessResponse(source=src)


class AIExtractionServicer(ai_extraction_pb2_grpc.AIExtractionServiceServicer):
    def ExtractEvents(self, request, context):
        _ctx(request.context)
        with operation("extraction", "ExtractEvents"):
            default_tz = request.context.default_timezone or "UTC"
            events, result = qwen_extraction.extract_events(request.text, default_tz)
            return ai_extraction_pb2.ExtractEventsResponse(
                events=[event_to_pb(e) for e in events],
                used_mock=result.used_mock, model=result.model, extraction_note=result.note)


class DateNormalizationServicer(date_normalization_pb2_grpc.DateNormalizationServiceServicer):
    def NormalizeEvents(self, request, context):
        _ctx(request.context)
        with operation("normalize", "NormalizeEvents"):
            default_tz = request.context.default_timezone or "UTC"
            out = [date_normalizer.normalize_event(event_from_pb(e), default_tz) for e in request.events]
            return date_normalization_pb2.NormalizeEventsResponse(events=[event_to_pb(e) for e in out])


class EventValidationServicer(event_validation_pb2_grpc.EventValidationServiceServicer):
    def ValidateEvents(self, request, context):
        _ctx(request.context)
        with operation("validation", "ValidateEvents"):
            out = [event_validation.validate_event(event_from_pb(e)) for e in request.events]
            return event_validation_pb2.ValidateEventsResponse(events=[event_to_pb(e) for e in out])


class ClarificationServicer(clarification_pb2_grpc.ClarificationServiceServicer):
    def GenerateClarificationQuestions(self, request, context):
        _ctx(request.context)
        with operation("clarification", "GenerateClarificationQuestions"):
            events = [event_from_pb(e) for e in request.events]
            qs = clarification.generate_questions(events)
            return clarification_pb2.GenerateQuestionsResponse(questions=[
                clarification_pb2.ClarificationQuestion(
                    id=q.id, event_id=q.event_id, field=q.field, question=q.question,
                    suggested_answers=q.suggested_answers) for q in qs])

    def ApplyClarificationAnswers(self, request, context):
        _ctx(request.context)
        with operation("clarification", "ApplyClarificationAnswers"):
            events = [event_from_pb(e) for e in request.events]
            answers = [{"event_id": a.event_id, "field": a.field, "answer": a.answer}
                       for a in request.answers]
            out = clarification.apply_answers(events, answers)
            # Re-normalize + re-validate after applying answers.
            out = [event_validation.validate_event(date_normalizer.normalize_event(e)) for e in out]
            return clarification_pb2.ApplyAnswersResponse(events=[event_to_pb(e) for e in out])


class ReminderServicer(reminder_pb2_grpc.ReminderServiceServicer):
    def ValidateReminderSettings(self, request, context):
        _ctx(request.context)
        with operation("reminder", "ValidateReminderSettings"):
            from .mapping import _UNIT_FROM_PB, _ANCHOR_FROM_PB, _UNIT_TO_PB, _ANCHOR_TO_PB, _SEV_TO_PB
            from ..schemas.event import Reminder, ReminderUnit, ReminderAnchor
            from ..grpc_gen import common_pb2 as pb
            reminders = [Reminder(amount=r.amount,
                                  unit=_UNIT_FROM_PB.get(r.unit, ReminderUnit.MINUTES),
                                  anchor=_ANCHOR_FROM_PB.get(r.anchor, ReminderAnchor.START))
                         for r in request.reminders]
            valid, issues, normalized = reminder_service.validate_reminders(reminders)
            resp = reminder_pb2.ValidateReminderSettingsResponse(valid=valid)
            for n in normalized:
                resp.normalized.append(pb.Reminder(
                    amount=n.amount, unit=_UNIT_TO_PB[n.unit], anchor=_ANCHOR_TO_PB[n.anchor]))
            for iss in issues:
                resp.issues.append(pb.ValidationIssue(
                    field=iss.field, code=iss.code, severity=_SEV_TO_PB[iss.severity],
                    message=iss.message, blocks_export=iss.blocks_export, suggestion=iss.suggestion or ""))
            return resp

    def BuildReminderSpecifications(self, request, context):
        _ctx(request.context)
        with operation("reminder", "BuildReminderSpecifications"):
            from .mapping import _UNIT_FROM_PB, _ANCHOR_FROM_PB
            from ..schemas.event import Reminder, ReminderUnit, ReminderAnchor
            events = [event_from_pb(e) for e in request.events]
            defaults = [Reminder(amount=r.amount,
                                 unit=_UNIT_FROM_PB.get(r.unit, ReminderUnit.MINUTES),
                                 anchor=_ANCHOR_FROM_PB.get(r.anchor, ReminderAnchor.START))
                        for r in request.default_reminders]
            out = reminder_service.build_specifications(events, defaults)
            return reminder_pb2.BuildReminderSpecsResponse(events=[event_to_pb(e) for e in out])


class ICSGenerationServicer(ics_generation_pb2_grpc.ICSGenerationServiceServicer):
    def GenerateCalendar(self, request, context):
        _ctx(request.context)
        with operation("ics", "GenerateCalendar"):
            events = [event_from_pb(e) for e in request.events]
            content = ics_generator.build_calendar(events, request.calendar_name or "My Events")
            return ics_generation_pb2.GenerateCalendarResponse(
                ics_content=content, event_count=sum(1 for e in events if e.start_date),
                content_type="text/calendar; charset=utf-8")


class ICSValidationServicer(ics_generation_pb2_grpc.ICSValidationServiceServicer):
    def ValidateCalendar(self, request, context):
        _ctx(request.context)
        with operation("ics", "ValidateCalendar"):
            expected = [event_from_pb(e) for e in request.expected_events]
            valid, count, issues = ics_validation.validate_calendar(request.ics_content, expected)
            resp = ics_generation_pb2.ValidateCalendarResponse(valid=valid, parsed_event_count=count)
            from .mapping import _SEV_TO_PB
            from ..grpc_gen import common_pb2 as pb
            for iss in issues:
                resp.issues.append(pb.ValidationIssue(
                    field=iss.field, code=iss.code, severity=_SEV_TO_PB[iss.severity],
                    message=iss.message, blocks_export=iss.blocks_export, suggestion=iss.suggestion or ""))
            return resp


class ArtifactServicer(artifact_pb2_grpc.ArtifactServiceServicer):
    def CreateArtifact(self, request, context):
        _ctx(request.context)
        with operation("artifact", "CreateArtifact"):
            meta = artifact_service.store.create(
                request.content, request.content_type, request.suggested_filename)
            return artifact_pb2.CreateArtifactResponse(artifact=artifact_pb2.Artifact(
                artifact_id=meta.artifact_id, filename=meta.filename, content_type=meta.content_type,
                size_bytes=meta.size_bytes, expires_at_unix=meta.expires_at_unix))

    def GetArtifact(self, request, context):
        _ctx(request.context)
        with operation("artifact", "GetArtifact"):
            result = artifact_service.store.get(request.artifact_id)
            if result is None:
                context.abort(grpc.StatusCode.NOT_FOUND, "Artifact not found or expired.")
            meta, content = result
            return artifact_pb2.GetArtifactResponse(
                artifact=artifact_pb2.Artifact(
                    artifact_id=meta.artifact_id, filename=meta.filename, content_type=meta.content_type,
                    size_bytes=meta.size_bytes, expires_at_unix=meta.expires_at_unix),
                content=content)

    def DeleteArtifact(self, request, context):
        _ctx(request.context)
        with operation("artifact", "DeleteArtifact"):
            deleted = artifact_service.store.delete(request.artifact_id)
            return artifact_pb2.DeleteArtifactResponse(deleted=deleted)
