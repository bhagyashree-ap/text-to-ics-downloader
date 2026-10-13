"""Reminder validation + spec building (spec sections 4.7 & 14)."""
from __future__ import annotations

from ..schemas.event import (
    CanonicalEvent,
    IssueSeverity,
    Reminder,
    ReminderUnit,
    ValidationIssue,
)

# Max sensible offset to catch obviously wrong values (e.g. 10000 weeks).
_MAX_WEEKS = 52


def validate_reminders(reminders: list[Reminder]) -> tuple[bool, list[ValidationIssue], list[Reminder]]:
    issues: list[ValidationIssue] = []
    normalized: list[Reminder] = []
    seen: set[tuple] = set()

    for i, rem in enumerate(reminders):
        if rem.amount < 0:
            issues.append(ValidationIssue(
                field=f"reminders[{i}]", code="REMINDER_NEGATIVE", severity=IssueSeverity.ERROR,
                message="Reminder offset cannot be negative.", blocks_export=True,
            ))
            continue
        weeks = _to_weeks(rem)
        if weeks > _MAX_WEEKS:
            issues.append(ValidationIssue(
                field=f"reminders[{i}]", code="REMINDER_TOO_LARGE", severity=IssueSeverity.WARNING,
                message="Reminder offset is unusually large.", blocks_export=False,
            ))
        key = (rem.amount, rem.unit, rem.anchor)
        if key in seen:
            continue  # dedupe identical reminders
        seen.add(key)
        normalized.append(rem)

    valid = not any(i.severity == IssueSeverity.ERROR for i in issues)
    return valid, issues, normalized


def _to_weeks(rem: Reminder) -> float:
    factor = {
        ReminderUnit.MINUTES: 1 / (60 * 24 * 7),
        ReminderUnit.HOURS: 1 / (24 * 7),
        ReminderUnit.DAYS: 1 / 7,
        ReminderUnit.WEEKS: 1,
    }[rem.unit]
    return rem.amount * factor


def build_specifications(
    events: list[CanonicalEvent], default_reminders: list[Reminder]
) -> list[CanonicalEvent]:
    """Apply batch defaults to events without their own reminders; per-event wins."""
    for ev in events:
        if not ev.reminders and default_reminders:
            _, _, normalized = validate_reminders(list(default_reminders))
            ev.reminders = normalized
        else:
            _, _, normalized = validate_reminders(ev.reminders)
            ev.reminders = normalized
    return events
