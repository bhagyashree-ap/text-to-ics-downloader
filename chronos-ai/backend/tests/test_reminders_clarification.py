"""Reminder + clarification tests (spec section 22, cases 33-35, 10)."""
from __future__ import annotations

from datetime import date, time

from app.schemas.event import CanonicalEvent, EventCategory, Reminder, ReminderUnit
from app.services.clarification import apply_answers, generate_questions
from app.services.reminder_service import build_specifications, validate_reminders


def test_batch_default_applied_when_no_event_reminders():
    events = [CanonicalEvent(title="A", start_date=date(2026, 10, 20), start_time=time(9, 0),
                             timezone="UTC")]
    out = build_specifications(events, [Reminder(amount=10, unit=ReminderUnit.MINUTES)])
    assert len(out[0].reminders) == 1
    assert out[0].reminders[0].amount == 10


def test_event_reminders_override_default():
    events = [CanonicalEvent(title="A", start_date=date(2026, 10, 20), start_time=time(9, 0),
                             timezone="UTC",
                             reminders=[Reminder(amount=1, unit=ReminderUnit.DAYS)])]
    out = build_specifications(events, [Reminder(amount=10, unit=ReminderUnit.MINUTES)])
    assert len(out[0].reminders) == 1
    assert out[0].reminders[0].unit == ReminderUnit.DAYS


def test_duplicate_reminders_deduped():
    valid, _, normalized = validate_reminders([
        Reminder(amount=10, unit=ReminderUnit.MINUTES),
        Reminder(amount=10, unit=ReminderUnit.MINUTES),
    ])
    assert valid is True
    assert len(normalized) == 1


def test_clarification_question_for_missing_date():
    ev = CanonicalEvent(title="Mystery meeting", start_date=None)
    questions = generate_questions([ev])
    assert any(q.field == "start_date" for q in questions)


def test_clarification_applies_answer_and_sets_provenance():
    ev = CanonicalEvent(title="Meeting", start_date=None)
    [q] = [q for q in generate_questions([ev]) if q.field == "start_date"]
    out = apply_answers([ev], [{"event_id": ev.id, "field": "start_date", "answer": "2026-10-20"}])
    assert out[0].start_date == date(2026, 10, 20)
    assert any(p.field == "start_date" and p.provenance.value == "USER" for p in out[0].provenance)


def test_no_question_for_optional_location():
    ev = CanonicalEvent(title="Mtg", start_date=date(2026, 10, 20), start_time=time(9, 0),
                        end_time=time(10, 0), timezone="UTC")
    questions = generate_questions([ev])
    assert not any(q.field == "location" for q in questions)


def test_deadline_no_end_time_question():
    ev = CanonicalEvent(title="Paper", category=EventCategory.DEADLINE,
                        start_date=date(2026, 11, 12), start_time=time(23, 59), timezone="UTC")
    questions = generate_questions([ev])
    assert not any(q.field == "end_time" for q in questions)
