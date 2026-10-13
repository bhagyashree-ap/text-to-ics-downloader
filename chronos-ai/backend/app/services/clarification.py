"""Clarification workflow (spec sections 4.6 & 10).

Generates concise questions only for fields that genuinely block a correct event,
applies answers, and never asks about optional fields (e.g. location).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, time

from ..schemas.event import CanonicalEvent, Provenance, FieldProvenance


@dataclass
class Question:
    id: str
    event_id: str
    field: str
    question: str
    suggested_answers: list[str]


def generate_questions(events: list[CanonicalEvent]) -> list[Question]:
    questions: list[Question] = []
    for ev in events:
        if ev.start_date is None:
            questions.append(Question(
                id=uuid.uuid4().hex[:12], event_id=ev.id, field="start_date",
                question=f"What is the date for \"{ev.title or 'this event'}\"?",
                suggested_answers=[],
            ))
        # Ambiguity-driven questions (e.g., which Friday, ambiguous numeric date).
        for flag in ev.ambiguity_flags:
            if "ambiguous" in flag.lower() and "numeric" in flag.lower():
                questions.append(Question(
                    id=uuid.uuid4().hex[:12], event_id=ev.id, field="start_date",
                    question=f"The date for \"{ev.title}\" is ambiguous. Please confirm it (YYYY-MM-DD).",
                    suggested_answers=[],
                ))
            elif "which" in flag.lower() or "does not exist" in flag.lower():
                questions.append(Question(
                    id=uuid.uuid4().hex[:12], event_id=ev.id, field="start_date",
                    question=flag,
                    suggested_answers=[],
                ))
        # Missing end time only when a duration is required and none defaulted.
        if (
            not ev.all_day and ev.start_time is not None and ev.end_time is None
            and ev.category.value != "DEADLINE"
        ):
            questions.append(Question(
                id=uuid.uuid4().hex[:12], event_id=ev.id, field="end_time",
                question=f"What time does \"{ev.title}\" end?",
                suggested_answers=["+1 hour", "+30 minutes", "+2 hours"],
            ))
    return questions


def apply_answers(events: list[CanonicalEvent], answers: list[dict]) -> list[CanonicalEvent]:
    """answers: list of {event_id, field, answer}."""
    by_id = {e.id: e for e in events}
    for ans in answers:
        ev = by_id.get(ans.get("event_id"))
        if ev is None:
            continue
        field = ans.get("field")
        value = (ans.get("answer") or "").strip()
        if not value:
            continue
        _apply_one(ev, field, value)
        ev.provenance.append(FieldProvenance(field=field, provenance=Provenance.USER))
        # Clear ambiguity flags tied to this field so revalidation reflects the fix.
        ev.ambiguity_flags = [f for f in ev.ambiguity_flags if field not in f.lower()]
    return events


def _apply_one(ev: CanonicalEvent, field: str, value: str) -> None:
    if field == "start_date":
        try:
            ev.start_date = date.fromisoformat(value)
        except ValueError:
            pass
    elif field == "end_time":
        if value.startswith("+"):
            from datetime import datetime, timedelta
            minutes = _relative_minutes(value)
            if ev.start_date and ev.start_time and minutes:
                end = datetime.combine(ev.start_date, ev.start_time) + timedelta(minutes=minutes)
                ev.end_date, ev.end_time = end.date(), end.time()
        else:
            try:
                ev.end_time = time.fromisoformat(value)
                ev.end_date = ev.end_date or ev.start_date
            except ValueError:
                pass
    elif field == "timezone":
        ev.timezone = value
    elif field == "title":
        ev.title = value


def _relative_minutes(value: str) -> int:
    v = value[1:].strip().lower()
    if "hour" in v:
        num = "".join(c for c in v if c.isdigit()) or "1"
        return int(num) * 60
    if "min" in v:
        num = "".join(c for c in v if c.isdigit()) or "30"
        return int(num)
    return 0
