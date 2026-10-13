"""Map between generated protobuf `common_pb2.Event` and the Pydantic CanonicalEvent.

Keeping this in one place means the gRPC layer is a thin transport over the shared
service logic. Requires generated stubs (run `python scripts/gen_proto.py` first).
"""
from __future__ import annotations

from datetime import date, time

from ..grpc_gen import common_pb2 as pb
from ..schemas.event import (
    CanonicalEvent,
    EventCategory,
    FieldProvenance,
    IssueSeverity,
    Provenance,
    Recurrence,
    RecurrenceFreq,
    Reminder,
    ReminderAnchor,
    ReminderUnit,
    SourceEvidence,
    ValidationIssue,
    ValidationStatus,
)

# --- enum maps (pydantic value -> pb enum) ----------------------------------

_CAT_TO_PB = {
    EventCategory.MEETING: pb.EVENT_CATEGORY_MEETING,
    EventCategory.EXAM: pb.EVENT_CATEGORY_EXAM,
    EventCategory.DEADLINE: pb.EVENT_CATEGORY_DEADLINE,
    EventCategory.APPOINTMENT: pb.EVENT_CATEGORY_APPOINTMENT,
    EventCategory.TRAVEL: pb.EVENT_CATEGORY_TRAVEL,
    EventCategory.HOLIDAY: pb.EVENT_CATEGORY_HOLIDAY,
    EventCategory.CLASS: pb.EVENT_CATEGORY_CLASS,
    EventCategory.ANNOUNCEMENT: pb.EVENT_CATEGORY_ANNOUNCEMENT,
    EventCategory.OTHER: pb.EVENT_CATEGORY_OTHER,
}
_CAT_FROM_PB = {v: k for k, v in _CAT_TO_PB.items()}

_PROV_TO_PB = {
    Provenance.STATED: pb.PROVENANCE_STATED,
    Provenance.INFERRED: pb.PROVENANCE_INFERRED,
    Provenance.USER: pb.PROVENANCE_USER,
    Provenance.DEFAULTED: pb.PROVENANCE_DEFAULTED,
    Provenance.MISSING: pb.PROVENANCE_MISSING,
    Provenance.CONFLICTING: pb.PROVENANCE_CONFLICTING,
}
_PROV_FROM_PB = {v: k for k, v in _PROV_TO_PB.items()}

_STATUS_TO_PB = {
    ValidationStatus.VALID: pb.VALIDATION_STATUS_VALID,
    ValidationStatus.VALID_WITH_WARNINGS: pb.VALIDATION_STATUS_VALID_WITH_WARNINGS,
    ValidationStatus.REQUIRES_CLARIFICATION: pb.VALIDATION_STATUS_REQUIRES_CLARIFICATION,
    ValidationStatus.INVALID: pb.VALIDATION_STATUS_INVALID,
}
_STATUS_FROM_PB = {v: k for k, v in _STATUS_TO_PB.items()}

_SEV_TO_PB = {IssueSeverity.WARNING: pb.ISSUE_SEVERITY_WARNING, IssueSeverity.ERROR: pb.ISSUE_SEVERITY_ERROR}
_SEV_FROM_PB = {v: k for k, v in _SEV_TO_PB.items()}

_UNIT_TO_PB = {
    ReminderUnit.MINUTES: pb.REMINDER_UNIT_MINUTES, ReminderUnit.HOURS: pb.REMINDER_UNIT_HOURS,
    ReminderUnit.DAYS: pb.REMINDER_UNIT_DAYS, ReminderUnit.WEEKS: pb.REMINDER_UNIT_WEEKS,
}
_UNIT_FROM_PB = {v: k for k, v in _UNIT_TO_PB.items()}

_ANCHOR_TO_PB = {ReminderAnchor.START: pb.REMINDER_ANCHOR_START, ReminderAnchor.END: pb.REMINDER_ANCHOR_END}
_ANCHOR_FROM_PB = {v: k for k, v in _ANCHOR_TO_PB.items()}

_FREQ_TO_PB = {
    RecurrenceFreq.DAILY: pb.RECURRENCE_FREQ_DAILY, RecurrenceFreq.WEEKLY: pb.RECURRENCE_FREQ_WEEKLY,
    RecurrenceFreq.MONTHLY: pb.RECURRENCE_FREQ_MONTHLY, RecurrenceFreq.YEARLY: pb.RECURRENCE_FREQ_YEARLY,
}
_FREQ_FROM_PB = {v: k for k, v in _FREQ_TO_PB.items()}


def _date_to_pb(d: date | None):
    return pb.LocalDate(year=d.year, month=d.month, day=d.day) if d else None


def _date_from_pb(m) -> date | None:
    if m is None or (m.year == 0 and m.month == 0 and m.day == 0):
        return None
    return date(m.year, m.month, m.day)


def _time_to_pb(t: time | None):
    return pb.LocalTime(hour=t.hour, minute=t.minute, second=t.second) if t else None


def _time_from_pb(m, present: bool) -> time | None:
    if m is None or not present:
        return None
    return time(m.hour, m.minute, m.second)


def event_to_pb(ev: CanonicalEvent) -> "pb.Event":
    msg = pb.Event(
        id=ev.id,
        source_event_id=ev.source_event_id or "",
        title=ev.title,
        category=_CAT_TO_PB.get(ev.category, pb.EVENT_CATEGORY_OTHER),
        timezone=ev.timezone,
        all_day=ev.all_day,
        location=ev.location or "",
        description=ev.description or "",
        organizer_name=ev.organizer_name or "",
        organizer_email=ev.organizer_email or "",
        url=ev.url or "",
        validation_status=_STATUS_TO_PB.get(ev.validation_status, pb.VALIDATION_STATUS_UNSPECIFIED),
        missing_fields=ev.missing_fields,
        ambiguity_flags=ev.ambiguity_flags,
    )
    if ev.start_date:
        msg.start_date.CopyFrom(_date_to_pb(ev.start_date))
    if ev.start_time:
        msg.start_time.CopyFrom(_time_to_pb(ev.start_time))
    if ev.end_date:
        msg.end_date.CopyFrom(_date_to_pb(ev.end_date))
    if ev.end_time:
        msg.end_time.CopyFrom(_time_to_pb(ev.end_time))
    if ev.recurrence:
        r = ev.recurrence
        rec = pb.Recurrence(freq=_FREQ_TO_PB[r.freq], interval=r.interval, by_day=r.by_day,
                            count=r.count or 0)
        if r.until:
            rec.until.CopyFrom(_date_to_pb(r.until))
        msg.recurrence.CopyFrom(rec)
    for rem in ev.reminders:
        msg.reminders.append(pb.Reminder(
            amount=rem.amount, unit=_UNIT_TO_PB[rem.unit], anchor=_ANCHOR_TO_PB[rem.anchor]))
    for iss in ev.issues:
        msg.issues.append(pb.ValidationIssue(
            field=iss.field, code=iss.code, severity=_SEV_TO_PB[iss.severity],
            message=iss.message, blocks_export=iss.blocks_export, suggestion=iss.suggestion or ""))
    for e in ev.evidence:
        msg.evidence.append(pb.SourceEvidence(field=e.field, text=e.text))
    for p in ev.provenance:
        msg.provenance.append(pb.FieldProvenance(field=p.field, provenance=_PROV_TO_PB[p.provenance]))
    return msg


def event_from_pb(msg) -> CanonicalEvent:
    ev = CanonicalEvent(
        id=msg.id or None,
        source_event_id=msg.source_event_id or None,
        title=msg.title,
        category=_CAT_FROM_PB.get(msg.category, EventCategory.OTHER),
        timezone=msg.timezone or "UTC",
        all_day=msg.all_day,
        location=msg.location or None,
        description=msg.description or None,
        organizer_name=msg.organizer_name or None,
        organizer_email=msg.organizer_email or None,
        url=msg.url or None,
    )
    if ev.id is None:
        import uuid
        ev.id = uuid.uuid4().hex
    ev.start_date = _date_from_pb(msg.start_date) if msg.HasField("start_date") else None
    ev.start_time = _time_from_pb(msg.start_time, msg.HasField("start_time"))
    ev.end_date = _date_from_pb(msg.end_date) if msg.HasField("end_date") else None
    ev.end_time = _time_from_pb(msg.end_time, msg.HasField("end_time"))
    ev.missing_fields = list(msg.missing_fields)
    ev.ambiguity_flags = list(msg.ambiguity_flags)
    if msg.validation_status in _STATUS_FROM_PB:
        ev.validation_status = _STATUS_FROM_PB[msg.validation_status]
    if msg.HasField("recurrence"):
        r = msg.recurrence
        ev.recurrence = Recurrence(
            freq=_FREQ_FROM_PB.get(r.freq, RecurrenceFreq.WEEKLY),
            interval=r.interval or 1,
            by_day=list(r.by_day),
            count=r.count or None,
            until=_date_from_pb(r.until) if r.HasField("until") else None,
        )
    for rem in msg.reminders:
        ev.reminders.append(Reminder(
            amount=rem.amount, unit=_UNIT_FROM_PB.get(rem.unit, ReminderUnit.MINUTES),
            anchor=_ANCHOR_FROM_PB.get(rem.anchor, ReminderAnchor.START)))
    for iss in msg.issues:
        ev.issues.append(ValidationIssue(
            field=iss.field, code=iss.code, severity=_SEV_FROM_PB.get(iss.severity, IssueSeverity.WARNING),
            message=iss.message, blocks_export=iss.blocks_export, suggestion=iss.suggestion or None))
    for e in msg.evidence:
        ev.evidence.append(SourceEvidence(field=e.field, text=e.text))
    for p in msg.provenance:
        ev.provenance.append(FieldProvenance(field=p.field, provenance=_PROV_FROM_PB.get(p.provenance, Provenance.STATED)))
    return ev
