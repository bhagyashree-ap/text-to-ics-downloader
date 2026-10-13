"""Extraction + mock-provider tests (spec section 22, cases 1-9, 36)."""
from __future__ import annotations

from datetime import date

from app.services.qwen_extraction import extract_events


def _titles(events):
    return [e.title for e in events]


def test_single_meeting():
    text = "Team meeting October 20, 2026, 2 PM to 3 PM."
    events, result = extract_events(text, "America/New_York", today=date(2026, 10, 1))
    assert result.used_mock is True
    assert len(events) == 1
    ev = events[0]
    assert ev.start_date == date(2026, 10, 20)
    assert ev.start_time.hour == 14
    assert ev.end_time.hour == 15
    assert ev.category.value == "MEETING"


def test_single_exam():
    text = "Biology Exam 2 on November 5, 2026, from 9 AM to 11 AM."
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 1
    assert events[0].category.value == "EXAM"
    assert events[0].start_time.hour == 9
    assert events[0].end_time.hour == 11


def test_multi_event_schedule():
    text = (
        "Exam 1 on October 15, 2026 at 9 AM.\n\n"
        "Exam 2 on October 22, 2026 at 9 AM.\n\n"
        "Exam 3 on October 29, 2026 at 9 AM."
    )
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 3
    assert {e.start_date for e in events} == {
        date(2026, 10, 15), date(2026, 10, 22), date(2026, 10, 29)}


def test_email_multiple_meetings():
    text = (
        "Subject: Schedule\n\n"
        "Project kickoff meeting on November 2, 2026 at 10 AM.\n\n"
        "Design review meeting on November 9, 2026 at 2 PM."
    )
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) >= 2


def test_deadline_with_time():
    text = "Research paper due November 12, 2026 at 11:59 PM."
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 1
    assert events[0].category.value == "DEADLINE"
    assert events[0].start_time.hour == 23
    assert events[0].start_time.minute == 59


def test_all_day_holiday():
    text = "Company holiday on December 25, 2026."
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 1
    assert events[0].all_day is True
    assert events[0].start_time is None


def test_reminder_in_text():
    text = "Dentist appointment on October 18, 2026 at 3 PM, remind me 1 day before."
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 1
    assert len(events[0].reminders) == 1
    assert events[0].reminders[0].amount == 1
    assert events[0].reminders[0].unit.value == "DAYS"


def test_large_document_many_events():
    blocks = [f"Lecture {i} on November {i}, 2026 at 10 AM." for i in range(1, 15)]
    text = "\n\n".join(blocks)
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert len(events) == 14


def test_no_events_returns_empty():
    text = "Just some random prose with no dates or times whatsoever."
    events, _ = extract_events(text, "UTC", today=date(2026, 10, 1))
    assert events == []
