"""ICS generation using the icalendar library (spec sections 4.8, 12, 13).

Rules honored:
- The LLM never writes ICS; this deterministic code does.
- Local timed events use DTSTART;TZID=<iana> with local wall time.
- All-day events use date values with an EXCLUSIVE end date.
- Deadlines are a single instant (no fabricated duration).
- Reminders become VALARM components with negative/zero TRIGGER.
- Library handles escaping and line folding.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event as IcsEvent

from ..schemas.event import CanonicalEvent, ReminderAnchor, ReminderUnit

PRODID = "-//Chronos AI//Calendar Generator//EN"

_UNIT_DELTA = {
    ReminderUnit.MINUTES: lambda n: timedelta(minutes=n),
    ReminderUnit.HOURS: lambda n: timedelta(hours=n),
    ReminderUnit.DAYS: lambda n: timedelta(days=n),
    ReminderUnit.WEEKS: lambda n: timedelta(weeks=n),
}


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def build_calendar(events: list[CanonicalEvent], calendar_name: str = "My Events") -> bytes:
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)

    dtstamp = datetime.now(tz=ZoneInfo("UTC"))

    for ev in events:
        if ev.start_date is None:
            continue  # validation should have blocked this; skip defensively
        cal.add_component(_build_vevent(ev, dtstamp))

    return cal.to_ical()


def _build_vevent(ev: CanonicalEvent, dtstamp: datetime) -> IcsEvent:
    ve = IcsEvent()
    ve.add("uid", f"{ev.id or uuid.uuid4()}@chronos-ai")
    ve.add("dtstamp", dtstamp)
    ve.add("sequence", 0)
    ve.add("summary", ev.title or "Untitled event")

    if ev.all_day:
        start_d: date = ev.start_date
        ve.add("dtstart", start_d)
        # Exclusive end: a one-day event ends the NEXT day.
        end_d = ev.end_date if ev.end_date and ev.end_date > start_d else start_d
        ve.add("dtend", end_d + timedelta(days=1))
    else:
        tz = _tz(ev.timezone)
        start_dt = datetime.combine(ev.start_date, ev.start_time or datetime.min.time())
        start_dt = start_dt.replace(tzinfo=tz)
        ve.add("dtstart", start_dt)
        if ev.end_date and ev.end_time:
            end_dt = datetime.combine(ev.end_date, ev.end_time).replace(tzinfo=tz)
            ve.add("dtend", end_dt)

    if ev.location:
        ve.add("location", ev.location)
    if ev.url:
        ve.add("url", ev.url)
    if ev.description:
        ve.add("description", ev.description)
    if ev.organizer_email:
        organizer = f"mailto:{ev.organizer_email}"
        params = {"CN": ev.organizer_name} if ev.organizer_name else {}
        ve.add("organizer", organizer, parameters=params)
    ve.add("status", "CONFIRMED")

    if ev.recurrence is not None:
        ve.add("rrule", _rrule_dict(ev.recurrence))

    for rem in ev.reminders:
        ve.add_component(_build_alarm(ev, rem))

    return ve


def _rrule_dict(rec) -> dict:
    d: dict = {"FREQ": [rec.freq.value]}
    if rec.interval and rec.interval != 1:
        d["INTERVAL"] = [rec.interval]
    if rec.by_day:
        d["BYDAY"] = rec.by_day
    if rec.count is not None:
        d["COUNT"] = [rec.count]
    if rec.until is not None:
        d["UNTIL"] = [datetime.combine(rec.until, datetime.max.time()).replace(tzinfo=ZoneInfo("UTC"))]
    return d


def _build_alarm(ev: CanonicalEvent, rem) -> Alarm:
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", f"Reminder: {ev.title or 'Event'}")
    delta = _UNIT_DELTA[rem.unit](rem.amount)
    # Negative = before the anchor. For END anchor, icalendar needs related=END.
    trigger = -delta
    if rem.anchor == ReminderAnchor.END:
        alarm.add("trigger", trigger, parameters={"RELATED": "END"})
    else:
        alarm.add("trigger", trigger)
    return alarm
