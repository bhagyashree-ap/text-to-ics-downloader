"""Turn raw extracted events into normalized, validated events.

- Reconcile the LLM's ISO guess with the original phrase using dateparser.
- Default an end time when only a start is known.
- Convert recurrence phrases into RFC 5545 RRULE strings.
- Score confidence and attach human-readable warnings for the review UI.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from .config import settings
from .schema import (
    ExtractedEvent,
    ReminderUnit,
    ValidatedEvent,
    ValidatedReminder,
)


def _parse_datetime(iso: Optional[str], phrase: Optional[str], now: datetime) -> Optional[datetime]:
    """Prefer a valid ISO string; otherwise parse the natural-language phrase."""
    if iso:
        try:
            return datetime.fromisoformat(iso.replace("Z", ""))
        except ValueError:
            pass
    if phrase:
        try:
            import dateparser

            return dateparser.parse(
                phrase,
                settings={
                    "RELATIVE_BASE": now,
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
        except Exception:
            return None
    return None


_WEEKDAYS = {
    "monday": "MO", "mon": "MO",
    "tuesday": "TU", "tue": "TU", "tues": "TU",
    "wednesday": "WE", "wed": "WE",
    "thursday": "TH", "thu": "TH", "thur": "TH", "thurs": "TH",
    "friday": "FR", "fri": "FR",
    "saturday": "SA", "sat": "SA",
    "sunday": "SU", "sun": "SU",
}


def _recurrence_to_rrule(phrase: Optional[str]) -> Optional[str]:
    """Best-effort RRULE from a natural-language recurrence phrase."""
    if not phrase:
        return None
    p = phrase.lower()
    parts: List[str] = []

    if "weekday" in p:
        parts.append("FREQ=WEEKLY")
        parts.append("BYDAY=MO,TU,WE,TH,FR")
    elif "daily" in p or re.search(r"every\s+day", p):
        parts.append("FREQ=DAILY")
    elif "month" in p:
        parts.append("FREQ=MONTHLY")
    elif "year" in p or "annual" in p:
        parts.append("FREQ=YEARLY")
    else:
        # weekly is the common default ("every Monday", "weekly")
        days = [code for name, code in _WEEKDAYS.items() if re.search(rf"\b{name}\b", p)]
        parts.append("FREQ=WEEKLY")
        if days:
            # de-dup preserving order
            seen = []
            for d in days:
                if d not in seen:
                    seen.append(d)
            parts.append("BYDAY=" + ",".join(seen))

    # count / until
    m = re.search(r"(\d+)\s*(?:times|occurrences)", p)
    if m:
        parts.append(f"COUNT={m.group(1)}")

    return ";".join(parts)


def validate_events(
    raw: List[ExtractedEvent],
    timezone: str,
    now: Optional[datetime] = None,
) -> List[ValidatedEvent]:
    now = now or datetime.now()
    out: List[ValidatedEvent] = []

    for ev in raw:
        warnings: List[str] = []
        confidence = 1.0

        start_dt = _parse_datetime(ev.start, ev.start_phrase, now)
        end_dt = _parse_datetime(ev.end, ev.end_phrase, now)

        start_iso: Optional[str] = None
        end_iso: Optional[str] = None

        if start_dt is None:
            warnings.append("No start date/time could be determined — please set one.")
            confidence -= 0.5
        else:
            if ev.all_day:
                start_iso = start_dt.date().isoformat()
            else:
                start_iso = start_dt.replace(microsecond=0).isoformat()

                if end_dt is None:
                    end_dt = start_dt + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)
                    warnings.append(
                        f"No end time found — defaulted to {settings.DEFAULT_DURATION_MINUTES} minutes."
                    )
                    confidence -= 0.1
                end_iso = end_dt.replace(microsecond=0).isoformat()

                if end_dt <= start_dt:
                    warnings.append("End is not after start — please check.")
                    confidence -= 0.2

        if ev.all_day and end_dt:
            end_iso = end_dt.date().isoformat()

        # Low confidence if we only had a fuzzy phrase and no ISO from the model.
        if ev.start and not ev.start_phrase:
            pass
        elif ev.start_phrase and not ev.start:
            confidence -= 0.1
            warnings.append(f"Date parsed from phrase \"{ev.start_phrase}\" — please confirm.")

        rrule = _recurrence_to_rrule(ev.recurrence_phrase)
        if ev.recurrence_phrase and rrule:
            warnings.append(f"Recurrence interpreted from \"{ev.recurrence_phrase}\" as {rrule}.")

        reminders = [ValidatedReminder(amount=r.amount, unit=r.unit) for r in ev.reminders]

        out.append(
            ValidatedEvent(
                id=str(uuid.uuid4()),
                title=ev.title or "Untitled event",
                start=start_iso,
                end=end_iso,
                all_day=ev.all_day,
                timezone=timezone,
                location=ev.location,
                url=ev.url,
                description=ev.description,
                attendees=ev.attendees,
                rrule=rrule,
                recurrence_phrase=ev.recurrence_phrase,
                reminders=reminders,
                confidence=max(0.0, round(confidence, 2)),
                warnings=warnings,
                source_text=ev.source_text,
            )
        )

    return out
