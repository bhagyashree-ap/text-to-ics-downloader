"""Build a standards-compliant iCalendar (.ics) file from validated events.

The LLM never writes raw ICS; this code does. We rely on the `icalendar` library
for correct line folding, escaping, and property serialization (RFC 5545).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import List

from icalendar import Alarm, Calendar, Event

from .schema import ReminderUnit, ValidatedEvent

_PRODID = "-//text-to-ics-downloader//EN"

_UNIT_TO_TIMEDELTA = {
    ReminderUnit.minutes: lambda n: timedelta(minutes=n),
    ReminderUnit.hours: lambda n: timedelta(hours=n),
    ReminderUnit.days: lambda n: timedelta(days=n),
    ReminderUnit.weeks: lambda n: timedelta(weeks=n),
}


def _parse(value: str):
    """Parse an ISO string into a date (all-day) or naive datetime."""
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", ""))
    return date.fromisoformat(value)


def build_ics(events: List[ValidatedEvent], calendar_name: str = "My Events") -> str:
    cal = Calendar()
    cal.add("prodid", _PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)

    now = datetime.utcnow()

    for ev in events:
        if not ev.start:
            # Skip events with no usable start — the UI should have flagged these.
            continue

        vevent = Event()
        vevent.add("uid", f"{uuid.uuid4()}@text-to-ics-downloader")
        vevent.add("dtstamp", now)
        vevent.add("sequence", 0)
        vevent.add("summary", ev.title)

        start = _parse(ev.start)

        if ev.all_day or isinstance(start, date) and not isinstance(start, datetime):
            # All-day: date-only DTSTART, DTEND is exclusive (next day).
            start_date = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()
            vevent.add("dtstart", start_date)
            if ev.end and "T" not in ev.end:
                end_date = date.fromisoformat(ev.end)
                if end_date <= start_date:
                    end_date = start_date + timedelta(days=1)
            else:
                end_date = start_date + timedelta(days=1)
            vevent.add("dtend", end_date)
        else:
            # Timed event. We attach the IANA tz so calendars show the right wall time.
            try:
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(ev.timezone or "UTC")
                start = start.replace(tzinfo=tz)
            except Exception:
                pass
            vevent.add("dtstart", start)

            if ev.end:
                end = _parse(ev.end)
                try:
                    from zoneinfo import ZoneInfo

                    end = end.replace(tzinfo=ZoneInfo(ev.timezone or "UTC"))
                except Exception:
                    pass
                vevent.add("dtend", end)

        if ev.location:
            vevent.add("location", ev.location)

        description_parts = []
        if ev.description:
            description_parts.append(ev.description)
        if ev.url:
            vevent.add("url", ev.url)
            description_parts.append(ev.url)
        if description_parts:
            vevent.add("description", "\n".join(description_parts))

        for email in ev.attendees:
            vevent.add("attendee", f"mailto:{email}")

        if ev.rrule:
            # icalendar accepts an RRULE dict; parse "FREQ=WEEKLY;BYDAY=MO" into it.
            rrule_dict = {}
            for part in ev.rrule.split(";"):
                if "=" not in part:
                    continue
                key, val = part.split("=", 1)
                rrule_dict[key.strip().upper()] = [v.strip() for v in val.split(",")]
            if rrule_dict:
                vevent.add("rrule", rrule_dict)

        # Reminders → VALARM (DISPLAY alarms with a negative trigger before start).
        for rem in ev.reminders:
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"Reminder: {ev.title}")
            delta = _UNIT_TO_TIMEDELTA[rem.unit](rem.amount)
            alarm.add("trigger", -delta)  # negative = before start
            vevent.add_component(alarm)

        cal.add_component(vevent)

    return cal.to_ical().decode("utf-8")
