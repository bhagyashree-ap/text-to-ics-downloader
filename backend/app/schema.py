"""Shared event schema — the contract between extraction, validation, and ICS building.

This Pydantic model is also what we hand to vLLM as a JSON schema for guided
decoding, so Qwen3 is forced to emit exactly this shape.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ReminderUnit(str, Enum):
    minutes = "minutes"
    hours = "hours"
    days = "days"
    weeks = "weeks"


class Reminder(BaseModel):
    """A single alert before the event start (maps to a VALARM)."""

    amount: int = Field(..., ge=0, description="How many units before the event start.")
    unit: ReminderUnit = Field(ReminderUnit.minutes, description="Time unit for the reminder.")


class ExtractedEvent(BaseModel):
    """One calendar event. The LLM returns ISO-ish strings + the original phrase;
    the validator normalizes and the ICS builder serializes."""

    title: str = Field(..., description="Short event title / summary.")

    # The LLM returns a best-effort ISO 8601 datetime (local, no offset) when it can,
    # plus the raw phrase it saw. The validator reconciles these against today's date,
    # timezone, and locale. Either may be empty if unknown.
    start: Optional[str] = Field(
        None, description="Best-effort ISO 8601 start, e.g. 2026-03-14T15:00:00. Null if unknown."
    )
    start_phrase: Optional[str] = Field(
        None, description="The exact wording from the text, e.g. 'next Friday at 3pm'."
    )
    end: Optional[str] = Field(
        None, description="Best-effort ISO 8601 end. Null if unknown (we default a duration)."
    )
    end_phrase: Optional[str] = Field(None, description="Original end wording, if any.")

    all_day: bool = Field(False, description="True if this is an all-day / date-only event.")

    location: Optional[str] = Field(None, description="Physical location or meeting room.")
    url: Optional[str] = Field(None, description="Zoom/Meet/Teams or other link, if present.")
    description: Optional[str] = Field(None, description="Agenda / notes / extra details.")
    attendees: List[str] = Field(default_factory=list, description="Attendee email addresses.")

    # Recurrence as a raw phrase the validator turns into an RRULE string.
    recurrence_phrase: Optional[str] = Field(
        None, description="e.g. 'every Monday', 'weekly until June'. Null if one-off."
    )

    reminders: List[Reminder] = Field(
        default_factory=list, description="Reminders explicitly mentioned in the text."
    )

    source_text: Optional[str] = Field(
        None, description="The span of input text this event was derived from (for review)."
    )


class ExtractionResult(BaseModel):
    """What the LLM returns: a list of events. Wrapped so guided JSON has a root object."""

    events: List[ExtractedEvent] = Field(default_factory=list)


# --- API-facing models (after validation) -----------------------------------

class ValidatedReminder(BaseModel):
    amount: int
    unit: ReminderUnit


class ValidatedEvent(BaseModel):
    """Normalized event returned to the frontend for review and used to build ICS."""

    id: str = Field(..., description="Stable client-side id for this event in the batch.")
    title: str
    start: Optional[str] = Field(None, description="Normalized ISO 8601 start (local wall time).")
    end: Optional[str] = Field(None, description="Normalized ISO 8601 end.")
    all_day: bool = False
    timezone: str = Field("UTC", description="IANA timezone, e.g. 'America/New_York'.")
    location: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    rrule: Optional[str] = Field(None, description="RFC 5545 RRULE string, e.g. 'FREQ=WEEKLY'.")
    recurrence_phrase: Optional[str] = None
    reminders: List[ValidatedReminder] = Field(default_factory=list)

    # Review aids
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Overall extraction confidence.")
    warnings: List[str] = Field(default_factory=list, description="Ambiguities to review.")
    source_text: Optional[str] = None


# --- Request / response models -----------------------------------------------

class ExtractRequest(BaseModel):
    text: str = Field(..., description="Raw pasted text to extract events from.")
    timezone: str = Field("UTC", description="User's IANA timezone for resolving relative dates.")
    locale: str = Field("en-US", description="Locale, used for DD/MM vs MM/DD disambiguation.")


class ExtractResponse(BaseModel):
    events: List[ValidatedEvent]
    used_llm: bool = Field(..., description="True if the LLM extracted; False if fallback was used.")


class IcsRequest(BaseModel):
    events: List[ValidatedEvent]
    calendar_name: str = Field("My Events", description="Name shown for the calendar.")
