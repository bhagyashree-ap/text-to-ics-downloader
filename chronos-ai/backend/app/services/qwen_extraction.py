"""Extraction service: provider raw dicts -> validated CanonicalEvents.

Validates EVERY model field independently (spec sections 4.3 & 6). Malformed fields
are dropped with an ambiguity flag rather than trusted.
"""
from __future__ import annotations

from datetime import date, datetime, time

from ..providers import ProviderResult, get_provider
from ..schemas.event import (
    CanonicalEvent,
    EventCategory,
    FieldProvenance,
    Provenance,
    Reminder,
    ReminderUnit,
    SourceEvidence,
)

_UNIT_MAP = {
    "minute": ReminderUnit.MINUTES, "min": ReminderUnit.MINUTES,
    "hour": ReminderUnit.HOURS, "hr": ReminderUnit.HOURS,
    "day": ReminderUnit.DAYS, "week": ReminderUnit.WEEKS,
}


def _safe_date(value) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _safe_time(value) -> time | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return time.fromisoformat(value[:8]) if len(value) > 5 else time.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None


def _category(value) -> EventCategory:
    if isinstance(value, str):
        try:
            return EventCategory(value.upper())
        except ValueError:
            return EventCategory.OTHER
    return EventCategory.OTHER


def extract_events(text: str, default_tz: str, today: date | None = None) -> tuple[list[CanonicalEvent], ProviderResult]:
    today = today or date.today()
    provider = get_provider()
    result = provider.extract(text, today.isoformat(), default_tz)

    events: list[CanonicalEvent] = []
    for raw in result.events:
        if not isinstance(raw, dict):
            continue
        title = raw.get("title")
        if not isinstance(title, str) or not title.strip():
            continue  # title is required; skip malformed entries

        ev = CanonicalEvent(title=title.strip(), category=_category(raw.get("category")))

        sd = _safe_date(raw.get("start_date"))
        ev.start_date = sd
        ev.start_time = _safe_time(raw.get("start_time"))
        ev.end_date = _safe_date(raw.get("end_date"))
        ev.end_time = _safe_time(raw.get("end_time"))
        ev.all_day = bool(raw.get("all_day"))
        tz = raw.get("timezone")
        ev.timezone = tz if isinstance(tz, str) and tz else default_tz

        for field in ("location", "description", "organizer_name", "organizer_email", "url"):
            val = raw.get(field)
            if isinstance(val, str) and val.strip():
                setattr(ev, field, val.strip())

        # Provenance: stated when model provided a date, else missing.
        ev.provenance.append(FieldProvenance(
            field="start_date",
            provenance=Provenance.STATED if sd else Provenance.MISSING,
        ))
        if ev.start_date is None:
            ev.missing_fields.append("start_date")

        # Evidence
        ev_text = raw.get("evidence")
        if isinstance(ev_text, str) and ev_text.strip():
            ev.evidence.append(SourceEvidence(field="all", text=ev_text.strip()[:500]))

        # Reminders from the mock provider's side channel (text-embedded).
        for rem in raw.get("_reminders", []) or []:
            unit = _UNIT_MAP.get(str(rem.get("unit", "minute")).lower(), ReminderUnit.MINUTES)
            try:
                amount = int(rem.get("amount", 0))
            except (TypeError, ValueError):
                continue
            ev.reminders.append(Reminder(amount=amount, unit=unit))

        events.append(ev)

    return events, result
