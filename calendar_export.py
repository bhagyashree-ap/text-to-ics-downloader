from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from icalendar import Alarm, Calendar, Event

from event_utils import _parse_recurrence, calculate_end_datetime, check_zone, localize_event_time, parse_event_time
from models import CalendarRequest, ReminderInterval

router = APIRouter()


@router.post("/api/v1/calendar/generate")
def generate(body: CalendarRequest):
    zone = check_zone(body.timezone)
    cal = Calendar()
    cal.add("prodid", "-//Text to Calendar//EN")
    cal.add("version", "2.0")
    for item in body.events:
        if not item.title.strip():
            raise HTTPException(422, "Every event needs a title")
        if not item.date:
            raise HTTPException(422, f"'{item.title}' needs a date")
        try:
            start_date = date.fromisoformat(item.date)
        except ValueError as exc:
            raise HTTPException(422, f"Invalid date for '{item.title}'") from exc
        if item.start_time:
            start = parse_event_time(item, zone)
        else:
            if item.end_time:
                raise HTTPException(422, f"'{item.title}' needs a start time when an end time is set")
            try:
                start = date.fromisoformat(item.date)
            except ValueError as exc:
                raise HTTPException(422, f"Invalid date for '{item.title}'") from exc
        effective_end_time = item.end_time
        effective_end_date = item.end_date
        if item.duration_minutes and not item.end_time_manual and item.start_time:
            try:
                calculated_date, effective_end_time = calculate_end_datetime(
                    item.date, item.start_time, item.duration_minutes, start.tzinfo, item.title
                )
                if calculated_date != item.date and not item.end_date_manual:
                    effective_end_date = calculated_date
                elif calculated_date == item.date and not item.end_date_manual:
                    effective_end_date = None
            except (ValueError, OverflowError) as exc:
                raise HTTPException(422, f"Could not calculate duration for '{item.title}': {exc}") from exc
        try:
            final_date = date.fromisoformat(effective_end_date) if effective_end_date else start_date
        except ValueError as exc:
            raise HTTPException(422, f"Invalid end date for '{item.title}'") from exc
        if final_date < start_date:
            raise HTTPException(422, f"End date must be on or after start date for '{item.title}'")
        end = None
        if effective_end_time:
            try:
                naive_end = datetime.fromisoformat(f"{effective_end_date or item.date}T{effective_end_time}")
                end = localize_event_time(naive_end, start.tzinfo, item.title)
            except ValueError as exc:
                raise HTTPException(422, f"Invalid end time for '{item.title}': {exc}") from exc
            if end <= start:
                raise HTTPException(422, f"End time must be after start time for '{item.title}'")
        ev = Event()
        ev.add("uid", f"{uuid4()}@text-to-calendar")
        ev.add("dtstamp", datetime.now(timezone.utc))
        ev.add("dtstart", start)
        ev.add("summary", item.title)
        if end:
            ev.add("dtend", end)
        elif isinstance(start, date) and not isinstance(start, datetime):
            ev.add("dtend", final_date + timedelta(days=1))
        elif effective_end_date:
            naive_end = datetime.combine(final_date + timedelta(days=1), datetime.min.time())
            ev.add("dtend", localize_event_time(naive_end, start.tzinfo, item.title))
        if item.location:
            ev.add("location", item.location)
        if item.description:
            ev.add("description", item.description)
        if item.recurrence:
            try:
                rule = _parse_recurrence(item.recurrence)
                if "UNTIL" in rule and isinstance(start, datetime) != ("T" in rule["UNTIL"]):
                    raise ValueError("UNTIL must use the same date or date-time type as the event")
                ev.add("rrule", rule)
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, f"Invalid recurrence rule for '{item.title}': {exc}") from exc
        for reminder in item.reminders:
            if isinstance(reminder, ReminderInterval):
                factor = {"minutes": 1, "hours": 60, "days": 1440, "weeks": 10080}[reminder.unit]
                minutes = reminder.amount * factor
            else:
                minutes = reminder
            if minutes < 0 or minutes > 525600:
                raise HTTPException(422, "Reminder must be between 0 and 525600 minutes")
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", item.title)
            alarm.add("trigger", timedelta(minutes=-minutes))
            ev.add_component(alarm)
        cal.add_component(ev)
    payload = cal.to_ical()
    try:
        verified = Calendar.from_ical(payload)
        if len(verified.walk("VEVENT")) != len(body.events):
            raise ValueError("event count changed during serialization")
    except (ValueError, TypeError) as exc:
        raise HTTPException(500, f"Could not validate generated calendar: {exc}") from exc
    return Response(payload, media_type="text/calendar", headers={
        "Content-Disposition": 'attachment; filename="events.ics"'
    })
