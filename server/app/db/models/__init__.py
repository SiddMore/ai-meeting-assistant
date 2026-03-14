"""
Database models for AI Meeting Assistant.

This module exports all SQLAlchemy models so they're available for:
- Alembic migrations (auto-detects model changes)
- Session relationships
- Direct imports throughout the app
"""

from app.db.models.user import User
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.transcript import Transcript
from app.db.models.transcript_chunk import TranscriptChunk
from app.db.models.mom import MOM
from app.db.models.action_item import ActionItem, TaskStatus, TaskPriority
from app.db.models.calendar_event import CalendarEvent

__all__ = [
    "User",
    "Meeting",
    "MeetingStatus",
    "Transcript",
    "TranscriptChunk",
    "MOM",
    "ActionItem",
    "TaskStatus",
    "TaskPriority",
    "CalendarEvent",
]
