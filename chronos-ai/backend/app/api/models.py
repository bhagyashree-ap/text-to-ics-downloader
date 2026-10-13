"""HTTP API request/response models (spec section 17)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..schemas.event import CanonicalEvent, Reminder


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Raw text / email body to analyze.")
    email_subject: Optional[str] = None
    sender: Optional[str] = None
    input_type: str = Field("text", description="text | email")
    timezone: str = Field("UTC", description="User's IANA timezone preference.")
    locale: str = Field("en-US")


class ClarificationQuestionOut(BaseModel):
    id: str
    event_id: str
    field: str
    question: str
    suggested_answers: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    batch_id: str
    events: List[CanonicalEvent]
    questions: List[ClarificationQuestionOut] = Field(default_factory=list)
    used_mock: bool
    model: str
    status: str
    total_events: int
    valid_events: int
    events_with_warnings: int
    events_requiring_clarification: int


class ValidateRequest(BaseModel):
    events: List[CanonicalEvent]


class ValidateResponse(BaseModel):
    events: List[CanonicalEvent]


class ClarificationAnswerIn(BaseModel):
    question_id: str
    event_id: str
    field: str
    answer: str


class ClarificationsRequest(BaseModel):
    events: List[CanonicalEvent]
    answers: List[ClarificationAnswerIn]


class ReminderValidateRequest(BaseModel):
    reminders: List[Reminder]


class ReminderValidateResponse(BaseModel):
    valid: bool
    normalized: List[Reminder]
    issues: List[dict]


class GenerateRequest(BaseModel):
    events: List[CanonicalEvent]
    default_reminders: List[Reminder] = Field(default_factory=list)
    calendar_name: str = "My Events"


class GenerateResponse(BaseModel):
    artifact_id: str
    filename: str
    event_count: int
    ics_valid: bool
    validation_issues: List[dict] = Field(default_factory=list)
