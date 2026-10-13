"""ICS generation + semantic round-trip tests (spec section 22, cases 16-21, 40)."""
from __future__ import annotations

from datetime import date, time

from icalendar import Calendar

from app.schemas.event import (
    CanonicalEvent,
    EventCategory,
    Recurrence,
    RecurrenceFreq,
    Reminder,
    ReminderUnit,
)
from app.services.ics_generator import build_calendar
from app.services.ics_validation import validate_calendar


def _parse(ics: bytes) -> Calendar:
    return Calendar.from_ical(ics)


def test_timed_event_preserves_local_time():
    ev = CanonicalEvent(
        title="Exam 1", start_date=date(2026, 10, 15), start_time=time(9, 0),
        end_date=date(2026, 10, 15), end_time=time(10, 0), timezone="America/New_York")
    ics = build_calendar([ev], "Exams")
    cal = _parse(ics)
    vevent = next(cal.walk("VEVENT"))
    dtstart = vevent.get("dtstart").dt
    # Local wall time must be 09:00 in New York, not shifted.
    assert dtstart.hour == 9
    assert str(dtstart.tzinfo) == "America/New_York"


def test_all_day_exclusive_end():
    ev = CanonicalEvent(
        title="Holiday", all_day=True, start_date=date(2026, 12, 25), timezone="UTC",
        category=EventCategory.HOLIDAY)
    ics = build_calendar([ev])
    cal = _parse(ics)
    vevent = next(cal.walk("VEVENT"))
    assert vevent.get("dtstart").dt == date(2026, 12, 25)
    # Exclusive end = next day.
    assert vevent.get("dtend").dt == date(2026, 12, 26)


def test_multiple_reminders_as_valarms():
    ev = CanonicalEvent(
        title="Exam", start_date=date(2026, 11, 5), start_time=time(9, 0),
        end_time=time(11, 0), timezone="UTC",
        reminders=[
            Reminder(amount=1, unit=ReminderUnit.DAYS),
            Reminder(amount=1, unit=ReminderUnit.HOURS),
            Reminder(amount=15, unit=ReminderUnit.MINUTES),
        ])
    ics = build_calendar([ev])
    cal = _parse(ics)
    vevent = next(cal.walk("VEVENT"))
    valarms = list(vevent.walk("VALARM"))
    assert len(valarms) == 3


def test_unicode_title_preserved():
    ev = CanonicalEvent(
        title="Café ☕ Meeting — Zürich", start_date=date(2026, 10, 20),
        start_time=time(9, 0), end_time=time(10, 0), timezone="UTC")
    ics = build_calendar([ev])
    cal = _parse(ics)
    vevent = next(cal.walk("VEVENT"))
    assert str(vevent.get("summary")) == "Café ☕ Meeting — Zürich"


def test_description_special_chars_escaped():
    ev = CanonicalEvent(
        title="Mtg", start_date=date(2026, 10, 20), start_time=time(9, 0),
        end_time=time(10, 0), timezone="UTC",
        description="Line1, with; special\nLine2 chars")
    ics = build_calendar([ev])
    cal = _parse(ics)  # must round-trip without error
    vevent = next(cal.walk("VEVENT"))
    desc = str(vevent.get("description"))
    assert "Line1" in desc and "Line2" in desc


def test_recurring_weekly_rrule():
    ev = CanonicalEvent(
        title="Standup", start_date=date(2026, 11, 2), start_time=time(10, 0),
        end_time=time(11, 0), timezone="America/New_York",
        recurrence=Recurrence(freq=RecurrenceFreq.WEEKLY, by_day=["MO"], until=date(2026, 12, 21)))
    ics = build_calendar([ev])
    cal = _parse(ics)
    vevent = next(cal.walk("VEVENT"))
    rrule = vevent.get("rrule")
    assert rrule["FREQ"] == ["WEEKLY"]
    assert rrule["BYDAY"] == ["MO"]


def test_multiple_events_different_timezones():
    e1 = CanonicalEvent(title="NY call", start_date=date(2026, 11, 10), start_time=time(9, 0),
                        end_time=time(10, 0), timezone="America/New_York")
    e2 = CanonicalEvent(title="London call", start_date=date(2026, 11, 10), start_time=time(9, 0),
                        end_time=time(10, 0), timezone="Europe/London")
    ics = build_calendar([e1, e2])
    cal = _parse(ics)
    vevents = list(cal.walk("VEVENT"))
    assert len(vevents) == 2
    tzs = {str(ve.get("dtstart").dt.tzinfo) for ve in vevents}
    assert tzs == {"America/New_York", "Europe/London"}


def test_round_trip_semantic_validation_passes():
    events = [
        CanonicalEvent(title="Exam 1", start_date=date(2026, 10, 15), start_time=time(9, 0),
                       end_date=date(2026, 10, 15), end_time=time(10, 0),
                       timezone="America/New_York"),
        CanonicalEvent(title="Holiday", all_day=True, start_date=date(2026, 12, 25),
                       timezone="UTC", category=EventCategory.HOLIDAY),
    ]
    ics = build_calendar(events, "Mixed")
    valid, count, issues = validate_calendar(ics, events)
    assert valid is True, [i.message for i in issues]
    assert count == 2


def test_round_trip_detects_count_mismatch():
    ev = CanonicalEvent(title="Only one", start_date=date(2026, 10, 15), start_time=time(9, 0),
                        end_time=time(10, 0), timezone="UTC")
    ics = build_calendar([ev])
    # Expect two but only one in file -> mismatch error.
    extra = CanonicalEvent(title="Phantom", start_date=date(2026, 10, 16), start_time=time(9, 0),
                           timezone="UTC")
    valid, count, issues = validate_calendar(ics, [ev, extra])
    assert valid is False
    assert any(i.code in ("EVENT_COUNT_MISMATCH", "EVENT_NOT_FOUND") for i in issues)
