"""Date normalization + validation tests (spec section 22, cases 11-15, 37-39)."""
from __future__ import annotations

from datetime import date, time

from app.schemas.event import (
    CanonicalEvent,
    EventCategory,
    Recurrence,
    RecurrenceFreq,
)
from app.services.date_normalizer import normalize_event, weekday_matches
from app.services.event_validation import validate_event


def test_missing_end_time_defaults_for_meeting():
    ev = CanonicalEvent(
        title="Sync", category=EventCategory.MEETING,
        start_date=date(2026, 10, 20), start_time=time(14, 0), timezone="UTC")
    normalize_event(ev, "UTC")
    assert ev.end_time == time(15, 0)  # +60 default
    assert "end_time" in ev.missing_fields


def test_deadline_no_fabricated_duration():
    ev = CanonicalEvent(
        title="Paper due", category=EventCategory.DEADLINE,
        start_date=date(2026, 11, 12), start_time=time(23, 59), timezone="UTC")
    normalize_event(ev, "UTC")
    assert ev.end_time == time(23, 59)  # same instant, not +1h


def test_overnight_event_not_rejected():
    ev = CanonicalEvent(
        title="Night shift", category=EventCategory.OTHER,
        start_date=date(2026, 10, 20), start_time=time(22, 0),
        end_date=date(2026, 10, 20), end_time=time(6, 0), timezone="UTC")
    normalize_event(ev, "UTC")
    validate_event(ev)
    assert ev.end_date == date(2026, 10, 21)  # bumped to next day
    assert ev.validation_status.value != "INVALID"


def test_weekday_mismatch_detected():
    # Oct 15 2026 is a Thursday, not Friday.
    assert weekday_matches(date(2026, 10, 15), "Friday") is False
    assert weekday_matches(date(2026, 10, 15), "Thursday") is True


def test_invalid_timezone_flagged():
    ev = CanonicalEvent(
        title="Mtg", start_date=date(2026, 10, 20), start_time=time(9, 0),
        timezone="Mars/Phobos")
    normalize_event(ev, "UTC")
    assert ev.timezone == "UTC"
    assert any("Mars" in f for f in ev.ambiguity_flags)


def test_dst_spring_forward_gap_flagged():
    # 2026-03-08 02:30 America/New_York does not exist (spring forward).
    ev = CanonicalEvent(
        title="Early mtg", start_date=date(2026, 3, 8), start_time=time(2, 30),
        timezone="America/New_York")
    normalize_event(ev, "America/New_York")
    assert any("does not exist" in f for f in ev.ambiguity_flags)


def test_title_required_blocks_export():
    ev = CanonicalEvent(title="", start_date=date(2026, 10, 20), start_time=time(9, 0))
    validate_event(ev)
    assert ev.validation_status.value == "INVALID"
    assert any(i.code == "TITLE_MISSING" and i.blocks_export for i in ev.issues)


def test_end_before_start_invalid():
    ev = CanonicalEvent(
        title="Bad", start_date=date(2026, 10, 20), start_time=time(14, 0),
        end_date=date(2026, 10, 20), end_time=time(13, 0), timezone="UTC")
    # Not overnight-normalized here because we validate directly; end < start same day.
    validate_event(ev)
    assert any(i.code == "END_BEFORE_START" for i in ev.issues)


def test_recurrence_count_and_until_conflict():
    ev = CanonicalEvent(
        title="Standup", start_date=date(2026, 11, 2), start_time=time(10, 0), timezone="UTC",
        recurrence=Recurrence(freq=RecurrenceFreq.WEEKLY, count=5, until=date(2026, 12, 21)))
    validate_event(ev)
    assert any(i.code == "RRULE_COUNT_AND_UNTIL" for i in ev.issues)


def test_missing_location_is_optional():
    ev = CanonicalEvent(
        title="Mtg", start_date=date(2026, 10, 20), start_time=time(9, 0),
        end_time=time(10, 0), timezone="UTC")
    validate_event(ev)
    # No blocking issue for missing location.
    assert not any("location" in i.field for i in ev.issues if i.blocks_export)
