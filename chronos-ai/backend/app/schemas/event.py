"""Canonical event schema (Pydantic v2).

This is the single source of truth for an event as it flows through the pipeline:
extraction -> normalization -> validation -> clarification -> reminders -> ICS.

Design decisions (documented per spec section 7 & 9):
- Local wall-clock date/time is represented SEPARATELY from any UTC instant.
  We store `start_date` + `start_time` + `timezone` (IANA id), NOT a single UTC
  timestamp, so a 9 AM meeting stays 9 AM local across DST changes.
- All-day events use date-only fields and the exclusive-end convention is applied
  only at ICS-serialization time (not stored here).
- Every important field carries provenance so the UI can show whether a value was
  stated, inferred, user-supplied, defaulted, missing, or conflicting.
"""
from __future__ import annotations

import uuid
from datetime import date, time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --- enums -------------------------------------------------------------------

class EventCategory(str, Enum):
    MEETING = "MEETING"
    EXAM = "EXAM"
    DEADLINE = "DEADLINE"
    APPOINTMENT = "APPOINTMENT"
    TRAVEL = "TRAVEL"
    HOLIDAY = "HOLIDAY"
    CLASS = "CLASS"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    OTHER = "OTHER"


class Provenance(str, Enum):
    """Where a field's value came from (spec section 7)."""

    STATED = "STATED"          # explicitly present in the source text
    INFERRED = "INFERRED"      # inferred from surrounding context by the model
    USER = "USER"              # supplied/edited by the user
    DEFAULTED = "DEFAULTED"    # filled from an approved application default
    MISSING = "MISSING"        # not available
    CONFLICTING = "CONFLICTING"  # contradictory signals in the source


class ValidationStatus(str, Enum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    REQUIRES_CLARIFICATION = "REQUIRES_CLARIFICATION"
    INVALID = "INVALID"


class IssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class ReminderUnit(str, Enum):
    MINUTES = "MINUTES"
    HOURS = "HOURS"
    DAYS = "DAYS"
    WEEKS = "WEEKS"


class ReminderAnchor(str, Enum):
    START = "START"
    END = "END"


class RecurrenceFreq(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


# --- nested messages ---------------------------------------------------------

class Reminder(BaseModel):
    amount: int = Field(..., ge=0, description="Units before the anchor. 0 = at the anchor time.")
    unit: ReminderUnit = ReminderUnit.MINUTES
    anchor: ReminderAnchor = ReminderAnchor.START

    def as_label(self) -> str:
        if self.amount == 0:
            return f"At event {self.anchor.value.lower()}"
        return f"{self.amount} {self.unit.value.lower()} before {self.anchor.value.lower()}"


class Recurrence(BaseModel):
    """A representable subset of RFC 5545 RRULE. Validated before serialization."""

    freq: RecurrenceFreq
    interval: int = Field(1, ge=1)
    by_day: List[str] = Field(default_factory=list, description="e.g. ['MO','WE'] (RFC codes).")
    count: Optional[int] = Field(None, ge=1, description="Number of occurrences.")
    until: Optional[date] = Field(None, description="Inclusive last date (local).")

    def to_rrule_string(self) -> str:
        parts = [f"FREQ={self.freq.value}"]
        if self.interval and self.interval != 1:
            parts.append(f"INTERVAL={self.interval}")
        if self.by_day:
            parts.append("BYDAY=" + ",".join(self.by_day))
        if self.count is not None:
            parts.append(f"COUNT={self.count}")
        if self.until is not None:
            parts.append("UNTIL=" + self.until.strftime("%Y%m%d"))
        return ";".join(parts)


class SourceEvidence(BaseModel):
    """A span of the source text that justifies an extracted field."""

    field: str
    text: str


class FieldProvenance(BaseModel):
    field: str
    provenance: Provenance


class ValidationIssue(BaseModel):
    field: str
    code: str
    severity: IssueSeverity
    message: str
    blocks_export: bool = False
    suggestion: Optional[str] = None


# --- the canonical event -----------------------------------------------------

class CanonicalEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_event_id: Optional[str] = Field(None, description="Original id from an invite, if any.")

    title: str = ""
    category: EventCategory = EventCategory.OTHER

    # Local wall-clock representation (NOT a UTC instant).
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    timezone: str = Field("UTC", description="IANA tz id, e.g. 'America/New_York'.")
    all_day: bool = False

    location: Optional[str] = None
    description: Optional[str] = None
    organizer_name: Optional[str] = None
    organizer_email: Optional[str] = None
    url: Optional[str] = None

    recurrence: Optional[Recurrence] = None
    reminders: List[Reminder] = Field(default_factory=list)

    # Review / provenance aids
    validation_status: ValidationStatus = ValidationStatus.VALID
    issues: List[ValidationIssue] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    ambiguity_flags: List[str] = Field(default_factory=list)
    evidence: List[SourceEvidence] = Field(default_factory=list)
    provenance: List[FieldProvenance] = Field(default_factory=list)

    model_config = {"use_enum_values": False}

    @property
    def blocking_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.blocks_export]
