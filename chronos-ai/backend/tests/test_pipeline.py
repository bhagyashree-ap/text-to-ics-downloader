"""End-to-end pipeline (in-process, no network) + failure handling.

Spec section 22 integration + cases 28 (malformed model response). gRPC transport
tests live in test_grpc.py (require generated stubs).
"""
from __future__ import annotations

from datetime import date

from app.providers.base import ProviderResult
from app.services import (
    date_normalizer,
    event_validation,
    ics_generator,
    ics_validation,
    qwen_extraction,
    reminder_service,
)
from app.schemas.event import Reminder, ReminderUnit


def test_full_pipeline_text_to_ics():
    text = (
        "Subject: Fall schedule\n\n"
        "Team meeting on October 20, 2026 from 2 PM to 3 PM.\n\n"
        "Research paper due November 12, 2026 at 11:59 PM.\n\n"
        "Company holiday on December 25, 2026."
    )
    events, result = qwen_extraction.extract_events(text, "America/New_York", today=date(2026, 10, 1))
    assert result.used_mock is True
    assert len(events) == 3

    events = [date_normalizer.normalize_event(e, "America/New_York") for e in events]
    events = [event_validation.validate_event(e) for e in events]
    events = reminder_service.build_specifications(events, [Reminder(amount=1, unit=ReminderUnit.DAYS)])

    ics = ics_generator.build_calendar(events, "Fall")
    valid, count, issues = ics_validation.validate_calendar(ics, events)
    assert valid is True, [i.message for i in issues]
    assert count == 3

    text_ics = ics.decode("utf-8")
    assert "BEGIN:VCALENDAR" in text_ics
    assert text_ics.count("BEGIN:VEVENT") == 3
    assert "BEGIN:VALARM" in text_ics  # reminders applied


def test_malformed_model_response_safely_handled(monkeypatch):
    """If the provider returns junk entries, extraction drops them, never crashes."""
    class JunkProvider:
        def extract(self, text, today_iso, default_tz):
            return ProviderResult(events=[
                {"no_title": True},            # missing required title -> dropped
                {"title": ""},                 # empty title -> dropped
                {"title": "Good", "start_date": "2026-10-20", "start_time": "09:00",
                 "timezone": default_tz},
                {"title": "BadDate", "start_date": "not-a-date"},  # bad date -> kept, date None
            ], used_mock=True, model="junk")

    monkeypatch.setattr("app.services.qwen_extraction.get_provider", lambda: JunkProvider())
    events, _ = qwen_extraction.extract_events("x", "UTC", today=date(2026, 10, 1))
    titles = [e.title for e in events]
    assert "Good" in titles
    assert "BadDate" in titles
    assert "" not in titles
    bad = next(e for e in events if e.title == "BadDate")
    assert bad.start_date is None
