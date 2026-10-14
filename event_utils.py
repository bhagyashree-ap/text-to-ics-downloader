import calendar
import html
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from icalendar import Event

from models import EventData


def check_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise HTTPException(422, f"Unknown time zone: {name}")


def _normalize_timezone(value: Optional[str], fallback: str = "") -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    abbreviation = value.upper()
    if abbreviation == "CST":
        if fallback.startswith("America/"):
            return "America/Chicago"
        if fallback.startswith("Asia/"):
            return "Asia/Shanghai"
        return None
    if abbreviation == "IST":
        if fallback == "Asia/Kolkata":
            return fallback
        if fallback == "Europe/Dublin":
            return fallback
        if fallback == "Asia/Jerusalem":
            return fallback
        return None
    if abbreviation == "BST":
        if fallback.startswith("Europe/"):
            return "Europe/London"
        if fallback.startswith("Asia/"):
            return "Asia/Dhaka"
        return None
    aliases = {
        "UTC": "UTC", "GMT": "UTC", "ET": "America/New_York", "EST": "America/New_York",
        "EDT": "America/New_York", "CT": "America/Chicago", "CST": "America/Chicago",
        "CDT": "America/Chicago", "MT": "America/Denver", "MST": "America/Denver",
        "MDT": "America/Denver", "PT": "America/Los_Angeles", "PST": "America/Los_Angeles",
        "PDT": "America/Los_Angeles", "AKST": "America/Anchorage", "AKDT": "America/Anchorage",
        "HST": "Pacific/Honolulu", "CET": "Europe/Paris", "CEST": "Europe/Paris",
        "EET": "Europe/Helsinki", "EEST": "Europe/Helsinki",
    }
    return aliases.get(abbreviation, value)


def _normalize_time(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().upper().replace("A.M.", "AM").replace("P.M.", "PM")
    value = re.sub(r"(?<=\d)\.(?=\d{2}\s*(?:AM|PM))", ":", value)
    value = re.sub(r"^AT\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    if value == "NOON":
        return "12:00"
    if value == "MIDNIGHT":
        return "00:00"
    value = re.sub(r"\s+(?:EST|EDT|CST|CDT|MST|MDT|PST|PDT|ET|CT|MT|PT|UTC|GMT)$", "", value)
    if "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
        except ValueError:
            pass
    for pattern in ("%H:%M", "%H:%M:%S", "%H%M", "%I:%M %p", "%I:%M%p", "%I:%M:%S %p", "%I %p", "%I%p"):
        try:
            return datetime.strptime(value, pattern).strftime("%H:%M")
        except ValueError:
            continue
    return None


def _normalize_date(value: Optional[str], zone_name: str) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().strip(".,; ")
    value = re.sub(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"(\d{1,2})(st|nd|rd|th)\b", r"\1", value, flags=re.IGNORECASE)
    formats = (
        "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y",
        "%m/%d/%y", "%d/%m/%y",
    )
    if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", value):
        first, second, year = map(int, re.split(r"[/.\-]", value))
        if first <= 12 and second <= 12:
            if zone_name.startswith("America/"):
                formats = ("%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y", "%m/%d/%y", "%m-%d-%y", "%m.%d.%y", "%d/%m/%Y", "%d/%m/%y")
            elif zone_name.startswith(("Europe/", "Asia/", "Africa/", "Australia/")):
                formats = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y", "%m/%d/%Y", "%m/%d/%y")
            else:
                return None
    for pattern in formats:
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _normalize_model_datetime(value: Optional[str], zone_name: str):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(check_zone(zone_name))
        return parsed.date().isoformat(), parsed.strftime("%H:%M")
    except (ValueError, HTTPException):
        return None


def _duration_minutes(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 < value <= 525600 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and 0 < value <= 525600 else None
    if not isinstance(value, str) or not value.strip():
        return None
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*(days?|d|hours?|hrs?|h|minutes?|mins?|m)\b", value, re.IGNORECASE)
    if not parts:
        return None
    factors = {"d": 1440, "day": 1440, "days": 1440, "h": 60, "hr": 60, "hrs": 60,
               "hour": 60, "hours": 60, "m": 1, "min": 1, "mins": 1, "minute": 1, "minutes": 1}
    total = 0.0
    for amount, unit in parts:
        try:
            value = float(amount)
        except (OverflowError, ValueError):
            return None
        if not 0 < value <= 525600:
            return None
        total += value * factors[unit.casefold()]
        if total > 525600:
            return None
    return int(total) if total.is_integer() and total > 0 else None


def _clean_input(text: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?i)</t[dh]\s*>", "\t", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def _tabular_schedule_events(text: str, timezone_name: str) -> List[dict]:
    events = []
    for line in text.splitlines():
        columns = line.strip().split("\t")
        if len(columns) < 12 or not columns[0].strip().isdigit():
            continue
        event_date = _normalize_date(columns[1], timezone_name)
        if not event_date:
            continue
        title = columns[4].strip()
        start_time = _normalize_time(columns[9])
        end_time = _normalize_time(columns[10])
        if not title:
            continue
        events.append({
            "title": title,
            "date": event_date,
            "start_time": start_time,
            "end_time": end_time,
            "location": columns[11].strip(),
        })
    return events


def _zoom_invitation_events(text: str, fallback_timezone: str) -> List[dict]:
    if "zoom.us" not in text.casefold() or not re.search(r"\bMeeting\s+ID\b", text, re.IGNORECASE):
        return []
    lines = text.splitlines()
    month_names = "|".join(calendar.month_name[1:] + [name[:3] for name in calendar.month_name[1:]])
    date_time_pattern = re.compile(
        rf"({month_names})\s+(\d{{1,2}}),?\s+(\d{{4}})\s+(\d{{1,2}}:\d{{2}}\s*[AP]M)",
        re.IGNORECASE,
    )
    timezone_names = {
        "eastern time": "America/New_York",
        "central time": "America/Chicago",
        "mountain time": "America/Denver",
        "pacific time": "America/Los_Angeles",
        "alaska time": "America/Anchorage",
        "hawaii time": "Pacific/Honolulu",
    }
    events = []
    for index, line in enumerate(lines):
        label = re.search(r"\bDate\s*&\s*Time\b", line, re.IGNORECASE)
        if not label:
            continue
        value = line[label.end():] + " " + " ".join(lines[index + 1:index + 3])
        match = date_time_pattern.search(value)
        if not match:
            continue
        month, day, year, raw_start = match.groups()
        event_date = _normalize_date(f"{month} {day}, {year}", fallback_timezone)
        start_time = _normalize_time(raw_start)
        if not event_date or not start_time:
            continue

        title = ""
        for previous in reversed(lines[max(0, index - 6):index]):
            candidate = previous.strip()
            if (candidate and len(candidate) <= 180 and
                    not re.search(r"(?:hello|thank you|meeting below|date\s*&\s*time|logo)", candidate, re.IGNORECASE)):
                title = candidate
                break
        if not title:
            continue

        timezone_name = fallback_timezone
        for phrase, zone_name in timezone_names.items():
            if re.search(rf"\b{re.escape(phrase)}\b", value, re.IGNORECASE):
                timezone_name = zone_name
                break
        timezone_quote = next((phrase for phrase in timezone_names if re.search(
            rf"\b{re.escape(phrase)}\b", value, re.IGNORECASE)), "")

        end_time = None
        time_range = re.compile(
            r"\bat\s+(\d{1,2}:\d{2}\s*[AP]M)\s*(?:-|–|—|to|through)\s*(\d{1,2}:\d{2}\s*[AP]M)\b",
            re.IGNORECASE,
        )
        for summary in lines:
            if title.casefold() not in summary.casefold():
                continue
            range_match = time_range.search(summary)
            if range_match and _normalize_time(range_match.group(1)) == start_time:
                end_time = _normalize_time(range_match.group(2))
                break

        meeting_id_match = re.search(r"\bMeeting\s+ID\s*:?\s*([\d\s-]{6,})", text, re.IGNORECASE)
        meeting_id = re.sub(r"\D", "", meeting_id_match.group(1)) if meeting_id_match else ""
        meeting_id_quote = next((" ".join(candidate.split()) for candidate in lines
            if meeting_id and re.search(r"\bMeeting\s+ID\b", candidate, re.IGNORECASE)
            and meeting_id in re.sub(r"\D", "", candidate)), "")
        join_match = re.search(r"https?://[^\s<>|]*zoom\.us/(?:j|w)/[^\s<>|]+", text, re.IGNORECASE)
        location = join_match.group(0).rstrip(".,);]") if join_match else ""
        description = f"Meeting ID: {meeting_id}" if meeting_id else ""
        date_quote = match.group(0)
        evidence = {"title": title, "date": date_quote, "start_time": raw_start}
        if end_time:
            evidence["end_time"] = next((" ".join(summary.split()) for summary in lines
                if title.casefold() in summary.casefold() and time_range.search(summary)), end_time)
        if timezone_quote:
            evidence["timezone"] = timezone_quote
        if location:
            evidence["location"] = location
        if description:
            evidence["description"] = meeting_id_quote or description
        events.append({
            "title": title,
            "date": event_date,
            "start_time": start_time,
            "end_time": end_time,
            "end_date": None,
            "location": location,
            "description": description,
            "timezone": timezone_name,
            "reminders": [],
            "evidence": evidence,
        })
    return events


def _deadline_task_details(item: dict, text: str, timezone_name: str) -> Optional[dict]:
    event_date = _normalize_date(item.get("date"), timezone_name)
    if not event_date:
        return None
    parsed_date = date.fromisoformat(event_date)
    month = parsed_date.strftime("%B")
    short_month = parsed_date.strftime("%b")
    year = parsed_date.year
    day = parsed_date.day
    date_pattern = re.compile(
        rf"(?:\b(?:{month}|{short_month})\s+0?{day},?\s+{year}\b|"
        rf"\b0?{day}\s+(?:{month}|{short_month}),?\s+{year}\b|"
        rf"\b{parsed_date.month}/0?{day}/{year}\b)", re.IGNORECASE,
    )
    for line in text.splitlines():
        date_match = date_pattern.search(line)
        if not date_match:
            continue
        has_deadline = re.search(r"\b(?:before|by|due|deadline|expires?)\b", line, re.IGNORECASE)
        has_task = re.search(r"\b(?:take|complete|finish|submit|attempt)\b.{0,100}\b(?:assessment|exam|test|challenge|screening|application)\b|\b(?:assessment|exam|test|challenge|screening|application)\b.{0,100}\b(?:take|complete|finish|submit|attempt)\b", line, re.IGNORECASE)
        if has_deadline and has_task:
            details = {"date": event_date, "start_time": None, "timezone": None}
            time_match = re.match(r"\s*,?\s*(\d{1,2}:\d{2}\s*[AP]M)\b", line[date_match.end():], re.IGNORECASE)
            if time_match:
                details["start_time"] = _normalize_time(time_match.group(1))
                details["time_quote"] = time_match.group(1)
            zone_match = re.search(r"\b(UTC|GMT|PDT|PST|MST|MDT|CST|CDT|EST|EDT|ET|CT|MT|PT)\b", line, re.IGNORECASE)
            if zone_match:
                details["timezone"] = _normalize_timezone(zone_match.group(1), timezone_name)
                details["timezone_quote"] = zone_match.group(1)
            details["date_quote"] = date_match.group(0)
            return details
    return None


def _explicit_reminders(text: str, event_title: Optional[str] = None) -> Optional[List[dict]]:
    instruction_lines = [line for line in text.splitlines()
                         if re.match(r"\s*(?:(?:[-*•]|\d+[.)])\s*)?(?:(?:please|can you)\s+)?(?:remind(?:\s+(?:me|us|everyone|attendees))?|set\s+(?:a\s+)?reminders?|add\s+(?:a\s+)?reminder|reminders?|alert(?:\s+me)?|notify(?:\s+me|\s+us)?)\b", line, re.IGNORECASE)
                         and not re.search(r"selected\s*:|no reminders selected|select any number of reminders", line, re.IGNORECASE)]
    if not instruction_lines:
        return None
    unit_names = {
        "minute": "minutes", "minutes": "minutes", "min": "minutes", "mins": "minutes",
        "hour": "hours", "hours": "hours", "hr": "hours", "hrs": "hours",
        "day": "days", "days": "days", "week": "weeks", "weeks": "weeks",
    }
    reminders = []
    factors = {"minutes": 1, "hours": 60, "days": 1440, "weeks": 10080}
    reminder_pattern = re.compile(
        r"\b(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
        r"(minutes?|mins?|hours?|hrs?|days?|weeks?)"
        r"(?:\s+(before|prior(?:\s+to)?|in\s+advance|ahead(?:\s+of)?))?\b",
        re.IGNORECASE,
    )
    title = (event_title or "").casefold()
    selected_lines = []
    for line in instruction_lines:
        matches = list(reminder_pattern.finditer(line))
        if not matches:
            if not re.search(r"\bat\s+(?:the\s+)?event\s+time\b", line, re.IGNORECASE):
                continue
        prefix = line[:matches[0].start()] if matches else ""
        prefix = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", prefix).strip(" .,!;:")
        tail = line[matches[-1].end():].strip(" .,!;:") if matches else ""
        generic = re.compile(
            r"(?:(?:please\s+)?remind(?:\s+(?:me|us|everyone|attendees))?|"
            r"(?:set\s+(?:a\s+)?reminders?|add\s+(?:a\s+)?reminder|reminders?|"
            r"alert(?:\s+me)?|notify(?:\s+me|\s+us)?))?\s*"
            r"(?:(?:for\s+)?(?:each|every|all)\s+(?:of\s+)?(?:my\s+)?"
            r"(?:events?|meetings?|appointments?|classes?|exams?)|(?:for\s+)?the\s+event|"
            r"(?:an?|the)\s+(?:\d+\s+(?:minutes?|hours?)\s+)?"
            r"(?:event|meeting|appointment|class|exam)s?|"
            r"(?:event|meeting|appointment|class|exam)s?)?",
            re.IGNORECASE,
        )
        scoped_prefix = bool(prefix) and not generic.fullmatch(prefix)
        scoped_tail = bool(tail) and not generic.fullmatch(tail)
        specifically_named = bool(title and title in line.casefold())
        scoped = scoped_prefix or scoped_tail
        if (scoped or specifically_named) and not specifically_named:
            continue
        if not event_title and specifically_named:
            continue
        selected_lines.append(line)
    if not selected_lines:
        return None
    instruction = " ".join(selected_lines)
    if re.search(r"\bat\s+(?:the\s+)?event\s+time\b", instruction, re.IGNORECASE):
        reminders.append({"amount": 0, "unit": "minutes"})
    amount_names = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    seen = {0} if reminders else set()
    matches = list(reminder_pattern.finditer(instruction))
    previous_end = None
    for match in matches:
        amount_text, unit, qualifier = match.groups()
        separator = instruction[previous_end:match.start()] if previous_end is not None else ""
        if not qualifier and previous_end is not None and not re.fullmatch(r"\s*(?:,|and|&)\s*", separator, re.IGNORECASE):
            previous_end = match.end()
            continue
        amount = amount_names.get(amount_text.casefold(), amount_text)
        amount = int(amount)
        unit = unit_names[unit.casefold()]
        minutes = amount * factors[unit]
        if minutes not in seen:
            reminders.append({"amount": amount, "unit": unit})
            seen.add(minutes)
        previous_end = match.end()
    return reminders or None


def _explicit_date_ranges(text: str):
    month_names = list(calendar.month_name[1:])
    months = "|".join(month_names + [name[:3] for name in month_names])
    month_number = {name.casefold(): index for index, name in enumerate(calendar.month_name) if name}
    month_number.update({name[:3].casefold(): index for index, name in enumerate(calendar.month_name) if name})
    cross_month_pattern = re.compile(
        rf"\b({months})\s+(\d{{1,2}})\s*(?:-|–|—|to|through)\s*({months})\s+(\d{{1,2}}),?\s+(\d{{4}})\b",
        re.IGNORECASE,
    )
    pattern = re.compile(
        rf"\b({months})\s+(\d{{1,2}})(?:\s*(?:-|–|—|to|through)\s*(\d{{1,2}}))?,?\s+(\d{{4}})\b",
        re.IGNORECASE,
    )
    ranges = []
    for match in cross_month_pattern.finditer(text):
        start_month, start_day, end_month, end_day, year = match.groups()
        try:
            start_month_number = month_number[start_month.casefold()[:3]]
            end_month_number = month_number[end_month.casefold()[:3]]
            start_year = int(year) - (1 if start_month_number > end_month_number else 0)
            start = date(start_year, start_month_number, int(start_day))
            end = date(int(year), end_month_number, int(end_day))
            if end >= start:
                ranges.append((start.isoformat(), end.isoformat()))
        except (KeyError, ValueError):
            continue
    for match in pattern.finditer(text):
        month_name, first_day, last_day, year = match.groups()
        if not last_day:
            continue
        try:
            month = datetime.strptime(month_name[:3], "%b").month
            start = date(int(year), month, int(first_day))
            end = date(int(year), month, int(last_day))
            if end >= start:
                ranges.append((start.isoformat(), end.isoformat()))
        except ValueError:
            continue
    return ranges


def _parse_recurrence(value: str) -> dict:
    value = value.strip()
    if value.upper().startswith("RRULE:"):
        value = value[6:].strip()
    if not value or "\n" in value or "\r" in value:
        raise ValueError("Enter one RRULE such as FREQ=WEEKLY;INTERVAL=2")

    rule = {}
    allowed = {
        "FREQ", "UNTIL", "COUNT", "INTERVAL", "BYSECOND", "BYMINUTE", "BYHOUR",
        "BYDAY", "BYMONTHDAY", "BYYEARDAY", "BYWEEKNO", "BYMONTH", "BYSETPOS", "WKST",
    }
    for part in value.split(";"):
        if part.count("=") != 1:
            raise ValueError("Invalid RRULE component")
        key, component = (piece.strip().upper() for piece in part.split("=", 1))
        if key not in allowed or key in rule or not component:
            raise ValueError(f"Invalid or repeated RRULE component: {key or part}")
        rule[key] = component

    if rule.get("FREQ") not in {"SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
        raise ValueError("FREQ must be a valid iCalendar frequency")
    if "COUNT" in rule and "UNTIL" in rule:
        raise ValueError("COUNT and UNTIL cannot be used together")

    for key in ("COUNT", "INTERVAL"):
        if key in rule and (not rule[key].isdigit() or int(rule[key]) < 1):
            raise ValueError(f"{key} must be a positive integer")

    numeric_ranges = {
        "BYSECOND": (0, 60), "BYMINUTE": (0, 59), "BYHOUR": (0, 23),
        "BYMONTHDAY": (-31, 31), "BYYEARDAY": (-366, 366),
        "BYWEEKNO": (-53, 53), "BYMONTH": (1, 12), "BYSETPOS": (-366, 366),
    }
    for key, (minimum, maximum) in numeric_ranges.items():
        if key not in rule:
            continue
        try:
            numbers = [int(value) for value in rule[key].split(",")]
        except ValueError as exc:
            raise ValueError(f"{key} must contain comma-separated integers") from exc
        if any(number == 0 and key not in {"BYSECOND", "BYMINUTE", "BYHOUR", "BYMONTH"}
               or number < minimum or number > maximum for number in numbers):
            raise ValueError(f"{key} contains a value outside its valid range")

    weekdays = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
    if "WKST" in rule and rule["WKST"] not in weekdays:
        raise ValueError("WKST must be a weekday abbreviation")
    if "BYDAY" in rule:
        for value in rule["BYDAY"].split(","):
            match = re.fullmatch(r"([+-]?\d{1,2})?(MO|TU|WE|TH|FR|SA|SU)", value)
            if not match or (match.group(1) and int(match.group(1)) == 0):
                raise ValueError("BYDAY must contain weekday abbreviations, optionally with an ordinal")
            if match.group(1) and abs(int(match.group(1))) > 53:
                raise ValueError("BYDAY ordinal must be between -53 and 53")
    if "UNTIL" in rule:
        try:
            if re.fullmatch(r"\d{8}", rule["UNTIL"]):
                datetime.strptime(rule["UNTIL"], "%Y%m%d")
            elif re.fullmatch(r"\d{8}T\d{6}Z", rule["UNTIL"]):
                datetime.strptime(rule["UNTIL"], "%Y%m%dT%H%M%SZ")
            else:
                raise ValueError
        except ValueError as exc:
            raise ValueError("UNTIL must be a valid date or UTC date-time in iCalendar format") from exc

    frequency = rule["FREQ"]
    if frequency == "WEEKLY" and "BYMONTHDAY" in rule:
        raise ValueError("BYMONTHDAY cannot be used with WEEKLY frequency")
    if frequency in {"DAILY", "WEEKLY", "MONTHLY"} and "BYYEARDAY" in rule:
        raise ValueError("BYYEARDAY requires YEARLY frequency")
    if "BYWEEKNO" in rule and frequency != "YEARLY":
        raise ValueError("BYWEEKNO requires YEARLY frequency")
    if "BYSETPOS" in rule and not any(key.startswith("BY") and key != "BYSETPOS" for key in rule):
        raise ValueError("BYSETPOS requires another BY rule")
    if "BYDAY" in rule and any(re.match(r"[+-]?\d", day) for day in rule["BYDAY"].split(",")):
        if frequency not in {"MONTHLY", "YEARLY"} or "BYWEEKNO" in rule:
            raise ValueError("Ordinal BYDAY is only valid with MONTHLY or YEARLY frequency")

    probe = Event()
    probe.add("rrule", rule)
    probe.to_ical()
    return rule


def _valid_recurrence(value: str) -> bool:
    try:
        _parse_recurrence(value)
        return True
    except (ValueError, TypeError):
        return False


def parse_event_time(event: EventData, zone: ZoneInfo) -> datetime:
    if not event.date or not event.start_time:
        raise HTTPException(422, f"'{event.title}' needs a date and start time")
    try:
        naive = datetime.fromisoformat(f"{event.date}T{event.start_time}")
        tz = check_zone(event.timezone) if event.timezone else zone
        return localize_event_time(naive, tz, event.title)
    except ValueError as exc:
        raise HTTPException(422, f"Invalid date or time for '{event.title}': {exc}")


def localize_event_time(value: datetime, zone: ZoneInfo, title: str) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("use a local time without a UTC offset")
    candidates = [value.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
    valid = [candidate for candidate in candidates
             if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value]
    if not valid:
        raise ValueError("nonexistent local time during a daylight saving transition")
    if len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset():
        raise ValueError("ambiguous local time during a daylight saving transition")
    return valid[0]


def calculate_end_datetime(event_date: str, start_time: str, duration_minutes: int, zone: ZoneInfo, title: str):
    start_naive = datetime.fromisoformat(f"{event_date}T{start_time}")
    start = localize_event_time(start_naive, zone, title)
    end = (start.astimezone(timezone.utc) + timedelta(minutes=duration_minutes)).astimezone(zone)
    return end.date().isoformat(), end.strftime("%H:%M")
