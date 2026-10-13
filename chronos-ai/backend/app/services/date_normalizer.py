"""Deterministic date/time normalization (spec sections 4.4 & 9).

Operates on CanonicalEvent objects. Never trusts model timestamps blindly: it
re-derives/validates local dates and times, flags ambiguities and DST problems,
and keeps local wall-clock separate from any UTC instant.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..core.config import settings
from ..schemas.event import (
    CanonicalEvent,
    FieldProvenance,
    Provenance,
)

_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _valid_timezone(tz: str) -> bool:
    try:
        ZoneInfo(tz)
        return True
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False


def _set_provenance(event: CanonicalEvent, field: str, prov: Provenance) -> None:
    for fp in event.provenance:
        if fp.field == field:
            fp.provenance = prov
            return
    event.provenance.append(FieldProvenance(field=field, provenance=prov))


def normalize_event(event: CanonicalEvent, default_tz: Optional[str] = None) -> CanonicalEvent:
    default_tz = default_tz or settings.DEFAULT_TIMEZONE

    # --- timezone -----------------------------------------------------------
    if not event.timezone or not _valid_timezone(event.timezone):
        if event.timezone and not _valid_timezone(event.timezone):
            event.ambiguity_flags.append(f"Unknown timezone '{event.timezone}'; using {default_tz}.")
        event.timezone = default_tz if _valid_timezone(default_tz) else "UTC"
        _set_provenance(event, "timezone", Provenance.DEFAULTED)

    # --- all-day semantics --------------------------------------------------
    if event.all_day:
        event.start_time = None
        event.end_time = None
        # Exclusive end handled at ICS build; here we only ensure end_date >= start_date.
        if event.start_date and event.end_date and event.end_date < event.start_date:
            event.end_date = event.start_date
        return event

    # --- default an end for timed events, respecting category ---------------
    if event.start_date and event.start_time and event.end_time is None:
        # Deadlines are a single instant — do NOT fabricate a duration.
        if event.category.value == "DEADLINE":
            event.end_date = event.start_date
            event.end_time = event.start_time
            _set_provenance(event, "end_time", Provenance.INFERRED)
        else:
            start_dt = datetime.combine(event.start_date, event.start_time)
            end_dt = start_dt + timedelta(minutes=settings.DEFAULT_EVENT_DURATION_MINUTES)
            event.end_date = end_dt.date()
            event.end_time = end_dt.time()
            event.missing_fields.append("end_time")
            _set_provenance(event, "end_time", Provenance.DEFAULTED)

    # --- overnight handling: end clock earlier than start => next day -------
    if (
        event.start_date and event.start_time and event.end_time
        and event.end_date == event.start_date
        and event.end_time <= event.start_time
    ):
        event.end_date = event.start_date + timedelta(days=1)
        event.ambiguity_flags.append("End time is earlier than start; treated as overnight (next day).")

    # --- DST: detect nonexistent / ambiguous local times --------------------
    _check_dst(event)

    return event


def _check_dst(event: CanonicalEvent) -> None:
    if not (event.start_date and event.start_time) or not _valid_timezone(event.timezone):
        return
    tz = ZoneInfo(event.timezone)
    naive = datetime.combine(event.start_date, event.start_time)

    # Nonexistent (spring-forward gap): localizing then normalizing shifts the wall time.
    aware = naive.replace(tzinfo=tz)
    # fold=0 vs fold=1 differing UTC offset indicates an ambiguous (fall-back) time.
    off0 = naive.replace(tzinfo=tz, fold=0).utcoffset()
    off1 = naive.replace(tzinfo=tz, fold=1).utcoffset()
    if off0 != off1:
        event.ambiguity_flags.append(
            "Local start time is ambiguous due to a daylight-saving fall-back transition."
        )

    # Gap detection: round-trip through UTC and back; if wall time changed, it was nonexistent.
    roundtrip = aware.astimezone(ZoneInfo("UTC")).astimezone(tz)
    if roundtrip.replace(tzinfo=None) != naive:
        event.ambiguity_flags.append(
            "Local start time does not exist (daylight-saving spring-forward gap); please confirm."
        )


def weekday_matches(d: date, stated_weekday: str) -> Optional[bool]:
    """Return True/False if the stated weekday matches the date, or None if unknown."""
    stated = stated_weekday.strip().lower()
    for i, name in enumerate(_WEEKDAY_NAMES):
        if name.lower().startswith(stated) or stated.startswith(name.lower()[:3]):
            return d.weekday() == i
    return None
