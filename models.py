from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ReminderInterval(BaseModel):
    amount: int
    unit: Literal["minutes", "hours", "days", "weeks"] = "minutes"


class EventData(BaseModel):
    title: str = ""
    date: str = ""
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=525600)
    end_time_manual: bool = False
    end_date_manual: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    timezone: Optional[str] = None
    recurrence: Optional[str] = None
    reminders: List[Union[int, ReminderInterval]] = Field(default_factory=list)
    reminder_details: List[ReminderInterval] = Field(default_factory=list)
    evidence: Dict[str, str] = Field(default_factory=dict)
    review_notes: List[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    timezone: str = "UTC"


class CalendarRequest(BaseModel):
    events: List[EventData] = Field(min_length=1, max_length=200)
    timezone: str = "UTC"
