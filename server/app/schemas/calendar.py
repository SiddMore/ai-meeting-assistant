from datetime import datetime, date
from typing import Optional, Literal, List

from pydantic import BaseModel


CalendarProvider = Literal["google", "microsoft", "none"]
TaskStatus = Literal["todo", "in_progress", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high"]


class CalendarIntegrationStatus(BaseModel):
    provider: str
    connected: bool
    has_calendar_scopes: bool


class CalendarEventOut(BaseModel):
    id: str
    title: str
    start: datetime | date
    end: datetime | date
    provider: CalendarProvider
    status: TaskStatus
    priority: TaskPriority
    mom_id: Optional[str]
    action_item_id: str


class CalendarEventsResponse(BaseModel):
    events: List[CalendarEventOut]

