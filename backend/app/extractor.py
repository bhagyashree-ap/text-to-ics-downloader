"""Event extraction.

Primary path: Qwen3 on vLLM via an OpenAI-compatible endpoint, using guided JSON
decoding so the model is forced to emit our schema.

Fallback path: a small, dependency-light rules-based extractor so the app is fully
functional even with no model configured or reachable.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List, Tuple

from .config import settings
from .schema import ExtractedEvent, ExtractionResult, Reminder, ReminderUnit

SYSTEM_PROMPT = """You extract calendar events from arbitrary pasted text (emails, \
chat messages, spreadsheet rows, notes). Return ALL events you find.

Rules:
- Output ONLY JSON matching the provided schema. No prose, no markdown.
- For each event: a short `title`, a best-effort ISO 8601 `start` (local wall time, \
no timezone offset) when a date/time is present, and the exact original wording in \
`start_phrase`. Do the same for `end`/`end_phrase` when an end or duration is given.
- Set `all_day` true for date-only events.
- Capture `location`, `url` (Zoom/Meet/Teams), `attendees` (emails), and `description`.
- If the text implies repetition, put the wording in `recurrence_phrase` \
(e.g. "every Monday", "weekly until June"). Otherwise leave it null.
- If the text explicitly asks for a reminder (e.g. "remind me 2 days before"), add it \
to `reminders` with amount + unit. Do NOT invent reminders that aren't stated.
- Put the span of text an event came from in `source_text`.
- Today's date and the user's timezone are provided; resolve relative dates against them."""


def _build_user_prompt(text: str, now: datetime, timezone: str, locale: str) -> str:
    return (
        f"Today is {now.strftime('%A, %Y-%m-%d')}. "
        f"User timezone: {timezone}. Locale: {locale} "
        f"(use it to decide DD/MM vs MM/DD).\n\n"
        f"Extract every event from the following text:\n\n{text}\n\n/no_think"
    )


def extract(text: str, timezone: str, locale: str, now: datetime | None = None) -> Tuple[ExtractionResult, bool]:
    """Return (result, used_llm)."""
    now = now or datetime.now()
    if settings.llm_enabled:
        try:
            return _extract_with_llm(text, timezone, locale, now), True
        except Exception as exc:  # noqa: BLE001 — degrade gracefully to fallback
            print(f"[extractor] LLM path failed, using fallback: {exc}")
    return _extract_with_rules(text, now), False


# --- LLM path ----------------------------------------------------------------

def _extract_with_llm(text: str, timezone: str, locale: str, now: datetime) -> ExtractionResult:
    # Imported lazily so the app runs even if `openai` isn't installed.
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )

    schema = ExtractionResult.model_json_schema()

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(text, now, timezone, locale)},
        ],
        temperature=0,
        # vLLM guided decoding: constrain output to our JSON schema.
        extra_body={
            "guided_json": schema,
            "chat_template_kwargs": {"enable_thinking": False},  # Qwen3: no reasoning trace
        },
    )
    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)
    return ExtractionResult.model_validate(data)


# --- Rules-based fallback ----------------------------------------------------
# Deliberately small. Handles the common shapes: one event per non-empty line or
# TSV row, with a date-ish token and an optional time. Good enough to keep the
# product usable before Qwen3 is wired up; the LLM is a pure upgrade.

_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?\b", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://\S+")
_REMIND_RE = re.compile(
    r"remind(?:er)?(?:\s+me)?\s+(\d+)\s*(minute|min|hour|hr|day|week)s?\s+before",
    re.IGNORECASE,
)
_RECUR_RE = re.compile(
    r"\b(every|each|weekly|daily|monthly|weekdays?)\b", re.IGNORECASE
)

_UNIT_MAP = {
    "minute": ReminderUnit.minutes,
    "min": ReminderUnit.minutes,
    "hour": ReminderUnit.hours,
    "hr": ReminderUnit.hours,
    "day": ReminderUnit.days,
    "week": ReminderUnit.weeks,
}


def _split_candidates(text: str) -> List[str]:
    # TSV rows (pasted from a spreadsheet) → each row a candidate.
    if "\t" in text:
        return [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Otherwise, split on blank lines (paragraph = event) then fall back to lines.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return blocks
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _parse_reminder(segment: str) -> List[Reminder]:
    out: List[Reminder] = []
    for amount, unit in _REMIND_RE.findall(segment):
        out.append(Reminder(amount=int(amount), unit=_UNIT_MAP.get(unit.lower(), ReminderUnit.minutes)))
    return out


def _guess_title(segment: str) -> str:
    # Strip emails/urls, take the first chunk of words as a title.
    cleaned = _URL_RE.sub("", _EMAIL_RE.sub("", segment))
    # If TSV, the longest column is usually the topic.
    if "\t" in segment:
        cols = [c.strip() for c in segment.split("\t") if c.strip()]
        if cols:
            return max(cols, key=len)[:120]
    words = cleaned.strip().split()
    return (" ".join(words[:10]) or "Event")[:120]


def _extract_with_rules(text: str, now: datetime) -> ExtractionResult:
    try:
        import dateparser  # optional dependency
    except Exception:
        dateparser = None

    events: List[ExtractedEvent] = []
    for seg in _split_candidates(text):
        start_iso = None
        start_phrase = None
        all_day = False

        if dateparser is not None:
            parsed = dateparser.parse(
                seg,
                settings={
                    "RELATIVE_BASE": now,
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                },
            )
            if parsed is not None:
                start_phrase = seg
                has_time = bool(_TIME_RE.search(seg))
                all_day = not has_time
                start_iso = parsed.replace(microsecond=0).isoformat() if has_time else parsed.date().isoformat()

        # Only emit a candidate if it looks like it has a date or a reminder.
        reminders = _parse_reminder(seg)
        if start_iso is None and not reminders:
            continue

        events.append(
            ExtractedEvent(
                title=_guess_title(seg),
                start=start_iso,
                start_phrase=start_phrase,
                all_day=all_day,
                url=(_URL_RE.search(seg).group(0) if _URL_RE.search(seg) else None),
                attendees=_EMAIL_RE.findall(seg),
                recurrence_phrase=(_RECUR_RE.search(seg).group(0) if _RECUR_RE.search(seg) else None),
                reminders=reminders,
                source_text=seg,
            )
        )

    return ExtractionResult(events=events)
