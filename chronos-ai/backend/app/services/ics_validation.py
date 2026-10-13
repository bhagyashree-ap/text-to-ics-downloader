"""ICS validation: parse the generated file and verify it semantically matches the
canonical input events (spec sections 4.9 & 12). Syntax parsing alone is insufficient.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar

from ..schemas.event import CanonicalEvent, IssueSeverity, ValidationIssue


def validate_calendar(ics_content: bytes, expected: list[CanonicalEvent]) -> tuple[bool, int, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    try:
        cal = Calendar.from_ical(ics_content)
    except Exception as exc:  # noqa: BLE001
        return False, 0, [ValidationIssue(
            field="calendar", code="PARSE_FAILED", severity=IssueSeverity.ERROR,
            message=f"Generated ICS failed to parse: {exc}", blocks_export=True,
        )]

    vevents = [c for c in cal.walk("VEVENT")]
    exportable = [e for e in expected if e.start_date is not None]

    if len(vevents) != len(exportable):
        issues.append(ValidationIssue(
            field="calendar", code="EVENT_COUNT_MISMATCH", severity=IssueSeverity.ERROR,
            message=f"Expected {len(exportable)} events, parsed {len(vevents)}.",
            blocks_export=True,
        ))

    # Match by UID prefix (event id) and compare core fields.
    by_uid = {str(ve.get("uid", "")).split("@")[0]: ve for ve in vevents}
    for ev in exportable:
        ve = by_uid.get(ev.id)
        if ve is None:
            issues.append(ValidationIssue(
                field="uid", code="EVENT_NOT_FOUND", severity=IssueSeverity.ERROR,
                message=f"Event '{ev.title}' not found in generated calendar.",
                blocks_export=True,
            ))
            continue
        _compare_event(ev, ve, issues)

    valid = not any(i.severity == IssueSeverity.ERROR for i in issues)
    return valid, len(vevents), issues


def _compare_event(ev: CanonicalEvent, ve, issues: list[ValidationIssue]) -> None:
    # Title
    if str(ve.get("summary", "")) != (ev.title or "Untitled event"):
        issues.append(ValidationIssue(
            field="summary", code="TITLE_MISMATCH", severity=IssueSeverity.ERROR,
            message=f"Title mismatch for '{ev.title}'.", blocks_export=True,
        ))

    dtstart = ve.get("dtstart")
    if dtstart is None:
        issues.append(ValidationIssue(
            field="dtstart", code="DTSTART_MISSING", severity=IssueSeverity.ERROR,
            message=f"DTSTART missing for '{ev.title}'.", blocks_export=True,
        ))
        return
    val = dtstart.dt

    if ev.all_day:
        # Must be a date (not datetime), and the stored date must match.
        if isinstance(val, datetime) or not isinstance(val, date):
            issues.append(ValidationIssue(
                field="dtstart", code="ALLDAY_NOT_DATE", severity=IssueSeverity.ERROR,
                message=f"All-day event '{ev.title}' did not serialize as a date.",
                blocks_export=True,
            ))
        elif val != ev.start_date:
            issues.append(ValidationIssue(
                field="dtstart", code="ALLDAY_DATE_MISMATCH", severity=IssueSeverity.ERROR,
                message=f"All-day start date mismatch for '{ev.title}'.", blocks_export=True,
            ))
        # exclusive end check
        dtend = ve.get("dtend")
        if dtend is not None:
            expected_end = (ev.end_date or ev.start_date)
            if dtend.dt <= expected_end:
                issues.append(ValidationIssue(
                    field="dtend", code="ALLDAY_END_NOT_EXCLUSIVE", severity=IssueSeverity.ERROR,
                    message=f"All-day end date for '{ev.title}' is not exclusive.",
                    blocks_export=True,
                ))
    else:
        # Timed: compare the LOCAL wall time, not the UTC instant.
        if not isinstance(val, datetime):
            issues.append(ValidationIssue(
                field="dtstart", code="TIMED_NOT_DATETIME", severity=IssueSeverity.ERROR,
                message=f"Timed event '{ev.title}' did not serialize as a datetime.",
                blocks_export=True,
            ))
            return
        local = val.astimezone(ZoneInfo(ev.timezone)) if val.tzinfo else val
        if local.date() != ev.start_date or (
            ev.start_time and (local.hour, local.minute) != (ev.start_time.hour, ev.start_time.minute)
        ):
            issues.append(ValidationIssue(
                field="dtstart", code="LOCAL_TIME_MISMATCH", severity=IssueSeverity.ERROR,
                message=f"Local start time mismatch for '{ev.title}'.", blocks_export=True,
            ))

    # Reminders -> VALARM count
    valarms = [c for c in ve.walk("VALARM")]
    if len(valarms) != len(ev.reminders):
        issues.append(ValidationIssue(
            field="valarm", code="REMINDER_COUNT_MISMATCH", severity=IssueSeverity.ERROR,
            message=f"Expected {len(ev.reminders)} reminders for '{ev.title}', found {len(valarms)}.",
            blocks_export=True,
        ))
