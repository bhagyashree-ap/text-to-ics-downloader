"""Deterministic mock Qwen provider (spec sections 6 & 22).

Enables local development and the standard test suite WITHOUT model credentials.
It uses regex/heuristics to extract events deterministically. Mock mode is always
reported via ProviderResult.used_mock=True so the UI never presents it as real AI.
"""
from __future__ import annotations

import re
from datetime import datetime

from .base import ProviderResult, QwenProvider

_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], start=1)
}
for _abbr, _i in list(_MONTHS.items()):
    pass

_MONTH_ABBR = {name[:3]: idx for name, idx in _MONTHS.items()}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://\S+")
# A time must have either a meridiem (2 PM) or a colon (14:30) to count — this
# avoids matching bare numbers inside dates like "October 20, 2026".
_TIME_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?|\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)",
    re.IGNORECASE,
)
# "October 15, 2026" / "Oct 15 2026"
_MONTH_DATE_RE = re.compile(
    r"\b([A-Za-z]{3,9})\s+(\d{1,2})(?:,)?\s+(\d{4})\b"
)
# ISO 2026-10-15
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_REMIND_RE = re.compile(
    r"remind(?:er)?(?:\s+me)?\s+(\d+)\s*(minute|min|hour|hr|day|week)s?\s+before",
    re.IGNORECASE,
)
_RECUR_RE = re.compile(r"\b(every|each|weekly|daily|monthly|weekdays?)\b", re.IGNORECASE)
_DEADLINE_RE = re.compile(r"\b(due|deadline|submit|by)\b", re.IGNORECASE)
_ALLDAY_RE = re.compile(r"\b(holiday|all[- ]day|day off)\b", re.IGNORECASE)


def _to_24h(hour: int, minute: int, mer: str | None) -> tuple[int, int]:
    if mer:
        mer = mer.lower().replace(".", "")
        if mer == "pm" and hour != 12:
            hour += 12
        elif mer == "am" and hour == 12:
            hour = 0
    return hour, minute


def _parse_date(segment: str) -> str | None:
    m = _ISO_DATE_RE.search(segment)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _MONTH_DATE_RE.search(segment)
    if m:
        month_name = m.group(1).lower()
        month = _MONTHS.get(month_name) or _MONTH_ABBR.get(month_name[:3])
        if month:
            return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(2)):02d}"
    return None


def _parse_times(segment: str) -> tuple[str | None, str | None]:
    # Blank out any matched date span so digits inside a date are never read as times.
    masked = segment
    for dm in list(_ISO_DATE_RE.finditer(segment)) + list(_MONTH_DATE_RE.finditer(segment)):
        masked = masked[: dm.start()] + (" " * (dm.end() - dm.start())) + masked[dm.end():]

    times: list[str] = []
    for m in _TIME_RE.finditer(masked):
        if m.group(1) is not None:  # colon form: HH:MM [meridiem]
            hour, minute, mer = int(m.group(1)), int(m.group(2)), m.group(3)
        else:  # meridiem-only form: H [meridiem]
            hour, minute, mer = int(m.group(4)), 0, m.group(5)
        if hour > 23 or minute > 59:
            continue
        h, mi = _to_24h(hour, minute, mer)
        times.append(f"{h:02d}:{mi:02d}")

    start = times[0] if times else None
    end = times[1] if len(times) > 1 else None
    return start, end


def _category(segment: str) -> str:
    s = segment.lower()
    if _ALLDAY_RE.search(segment) or "holiday" in s:
        return "HOLIDAY"
    if _DEADLINE_RE.search(segment) and ("due" in s or "deadline" in s):
        return "DEADLINE"
    if "exam" in s or "test" in s:
        return "EXAM"
    if "flight" in s or "depart" in s or "arrive" in s:
        return "TRAVEL"
    if "appointment" in s or "dentist" in s or "doctor" in s:
        return "APPOINTMENT"
    if "meeting" in s or "standup" in s or "sync" in s or "call" in s:
        return "MEETING"
    if "class" in s or "lecture" in s:
        return "CLASS"
    return "OTHER"


def _title(segment: str) -> str:
    cleaned = _URL_RE.sub("", _EMAIL_RE.sub("", segment)).strip()
    # First sentence-ish chunk.
    words = re.split(r"[.\n]", cleaned)[0].strip()
    return (words[:120] or "Event")


def _split(text: str) -> list[str]:
    if "\t" in text:
        return [ln.strip() for ln in text.splitlines() if ln.strip()]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return blocks
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


class MockQwenProvider(QwenProvider):
    def extract(self, text: str, today_iso: str, default_tz: str) -> ProviderResult:
        events: list[dict] = []
        for seg in _split(text):
            d = _parse_date(seg)
            start_t, end_t = _parse_times(seg)
            reminders = _REMIND_RE.findall(seg)
            if d is None and not reminders:
                continue

            category = _category(seg)
            all_day = bool(_ALLDAY_RE.search(seg)) or (d is not None and start_t is None and category == "HOLIDAY")

            ev = {
                "title": _title(seg),
                "category": category,
                "start_date": d,
                "start_time": None if all_day else start_t,
                "end_date": None,
                "end_time": None if all_day else end_t,
                "timezone": default_tz,
                "all_day": all_day,
                "location": None,
                "description": None,
                "organizer_name": None,
                "organizer_email": (_EMAIL_RE.search(seg).group(0) if _EMAIL_RE.search(seg) else None),
                "url": (_URL_RE.search(seg).group(0) if _URL_RE.search(seg) else None),
                "recurrence_text": (_RECUR_RE.search(seg).group(0) if _RECUR_RE.search(seg) else None),
                "evidence": seg,
                "_reminders": [{"amount": int(a), "unit": u} for a, u in reminders],
            }
            events.append(ev)

        return ProviderResult(events=events, used_mock=True, model="mock-deterministic", note="")
