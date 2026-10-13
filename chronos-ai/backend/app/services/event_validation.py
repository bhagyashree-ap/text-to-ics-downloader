"""Deterministic event validation, independent of the LLM (spec sections 4.5 & 11)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..schemas.event import (
    CanonicalEvent,
    IssueSeverity,
    ValidationIssue,
    ValidationStatus,
)

_RFC_DAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}


def _valid_tz(tz: str) -> bool:
    try:
        ZoneInfo(tz)
        return True
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False


def validate_event(event: CanonicalEvent) -> CanonicalEvent:
    issues: list[ValidationIssue] = []

    # Title
    if not event.title or not event.title.strip():
        issues.append(ValidationIssue(
            field="title", code="TITLE_MISSING", severity=IssueSeverity.ERROR,
            message="Event title is required.", blocks_export=True,
            suggestion="Add a short title.",
        ))

    # Start date presence
    if event.start_date is None:
        issues.append(ValidationIssue(
            field="start_date", code="START_DATE_MISSING", severity=IssueSeverity.ERROR,
            message="A start date is required.", blocks_export=True,
            suggestion="Provide the event date.",
        ))

    # Timezone
    if not _valid_tz(event.timezone):
        issues.append(ValidationIssue(
            field="timezone", code="TZ_INVALID", severity=IssueSeverity.ERROR,
            message=f"Invalid timezone '{event.timezone}'.", blocks_export=True,
            suggestion="Select a valid IANA timezone.",
        ))

    # Timed-event specifics
    if not event.all_day:
        if event.start_date and event.start_time is None:
            issues.append(ValidationIssue(
                field="start_time", code="START_TIME_MISSING", severity=IssueSeverity.WARNING,
                message="No start time; mark as all-day or add a start time.", blocks_export=False,
                suggestion="Add a start time or set all-day.",
            ))
        # Start/end ordering (allow legitimate overnight: end_date after start_date)
        if (
            event.start_date and event.start_time
            and event.end_date and event.end_time
        ):
            start_dt = datetime.combine(event.start_date, event.start_time)
            end_dt = datetime.combine(event.end_date, event.end_time)
            if end_dt < start_dt:
                issues.append(ValidationIssue(
                    field="end_time", code="END_BEFORE_START", severity=IssueSeverity.ERROR,
                    message="Event end is before its start.", blocks_export=True,
                    suggestion="Fix the end date/time.",
                ))
            elif end_dt == start_dt and event.category.value != "DEADLINE":
                issues.append(ValidationIssue(
                    field="end_time", code="ZERO_DURATION", severity=IssueSeverity.WARNING,
                    message="Event has zero duration.", blocks_export=False,
                ))
    else:
        # all-day must not carry times
        if event.start_time or event.end_time:
            issues.append(ValidationIssue(
                field="all_day", code="ALLDAY_WITH_TIME", severity=IssueSeverity.WARNING,
                message="All-day event should not have specific times; times ignored.",
                blocks_export=False,
            ))

    # Recurrence
    if event.recurrence is not None:
        rec = event.recurrence
        for d in rec.by_day:
            if d not in _RFC_DAYS:
                issues.append(ValidationIssue(
                    field="recurrence", code="RRULE_BAD_DAY", severity=IssueSeverity.ERROR,
                    message=f"Invalid recurrence day '{d}'.", blocks_export=True,
                ))
        if rec.interval < 1:
            issues.append(ValidationIssue(
                field="recurrence", code="RRULE_BAD_INTERVAL", severity=IssueSeverity.ERROR,
                message="Recurrence interval must be >= 1.", blocks_export=True,
            ))
        if rec.count is not None and rec.until is not None:
            issues.append(ValidationIssue(
                field="recurrence", code="RRULE_COUNT_AND_UNTIL", severity=IssueSeverity.ERROR,
                message="Recurrence cannot set both COUNT and UNTIL.", blocks_export=True,
            ))

    # Reminders
    for i, rem in enumerate(event.reminders):
        if rem.amount < 0:
            issues.append(ValidationIssue(
                field=f"reminders[{i}]", code="REMINDER_NEGATIVE", severity=IssueSeverity.ERROR,
                message="Reminder offset cannot be negative.", blocks_export=True,
            ))

    # Carry ambiguity flags forward as clarification-worthy warnings.
    requires_clarification = bool(event.ambiguity_flags) or any(
        f in event.missing_fields for f in ("start_date", "timezone")
    )

    event.issues = issues
    event.validation_status = _status(issues, requires_clarification)
    return event


def _status(issues: list[ValidationIssue], requires_clarification: bool) -> ValidationStatus:
    if any(i.severity == IssueSeverity.ERROR for i in issues):
        return ValidationStatus.INVALID
    if requires_clarification:
        return ValidationStatus.REQUIRES_CLARIFICATION
    if any(i.severity == IssueSeverity.WARNING for i in issues):
        return ValidationStatus.VALID_WITH_WARNINGS
    return ValidationStatus.VALID
