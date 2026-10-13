"""Build an 'Add to Google Calendar' link for a single event.

This is a prefilled template URL — no OAuth, no API. The user clicks it and Google
opens a new-event page with the fields filled in. Best for a single event; for many
events the .ics import is the better path.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from .schema import ValidatedEvent

_BASE = "https://calendar.google.com/calendar/render"


def _fmt(value: str, all_day: bool) -> str:
    if all_day or "T" not in value:
        d = date.fromisoformat(value[:10])
        return d.strftime("%Y%m%d")
    dt = datetime.fromisoformat(value.replace("Z", ""))
    # Google reads this as local time when no Z/offset is given here; we pass the
    # ctz param alongside so it is interpreted in the event's timezone.
    return dt.strftime("%Y%m%dT%H%M%S")


def google_calendar_link(ev: ValidatedEvent) -> str | None:
    if not ev.start:
        return None

    if ev.all_day or "T" not in ev.start:
        start = _fmt(ev.start, True)
        if ev.end and "T" not in ev.end:
            end = _fmt(ev.end, True)
        else:
            end = (date.fromisoformat(ev.start[:10]) + timedelta(days=1)).strftime("%Y%m%d")
        dates = f"{start}/{end}"
    else:
        start = _fmt(ev.start, False)
        end = _fmt(ev.end, False) if ev.end else _fmt(ev.start, False)
        dates = f"{start}/{end}"

    details = []
    if ev.description:
        details.append(ev.description)
    if ev.url:
        details.append(ev.url)

    params = {
        "action": "TEMPLATE",
        "text": ev.title,
        "dates": dates,
    }
    if details:
        params["details"] = "\n".join(details)
    if ev.location:
        params["location"] = ev.location
    if ev.timezone and not ev.all_day:
        params["ctz"] = ev.timezone
    if ev.rrule:
        params["recur"] = f"RRULE:{ev.rrule}"

    return f"{_BASE}?{urlencode(params)}"
