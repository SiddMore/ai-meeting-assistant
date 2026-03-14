from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.meeting import MeetingListItem


class ActionItemOut(BaseModel):
    """Action item response model."""
    id: str
    task: str
    assignee_name: Optional[str]
    assignee_email: Optional[str]
    deadline: Optional[str]  # ISO date string
    status: str
    priority: str
    created_at: str  # ISO datetime string

    class Config:
        from_attributes = True


class MOMListItem(BaseModel):
    """MOM list item for overview."""
    id: str
    meeting: MeetingListItem
    summary: Optional[str]
    created_at: str  # ISO datetime string

    class Config:
        from_attributes = True


class MOMOut(BaseModel):
    """Full MOM response model."""
    id: str
    meeting_id: str
    summary: Optional[str]
    key_decisions: Optional[str]
    full_content: Optional[str]
    pdf_url: Optional[str]
    email_sent: bool
    sent_at: Optional[str]  # ISO datetime string
    created_at: str  # ISO datetime string
    action_items: List[ActionItemOut]

    class Config:
        from_attributes = True