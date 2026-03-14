"""
meeting.py — Pydantic schemas for the meetings API.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, field_validator


# ── Enums (mirrors DB models) ──────────────────────────────────────────────────

class MeetingPlatform(str):
    google_meet = "google_meet"
    zoom = "zoom"
    teams = "teams"
    other = "other"


# ── Create ─────────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: Optional[str] = None
    platform: str  # google_meet | zoom | teams | other
    meeting_url: str

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"google_meet", "zoom", "teams", "other"}
        if v not in allowed:
            raise ValueError(f"platform must be one of {allowed}")
        return v

    @field_validator("meeting_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("meeting_url must be a valid HTTP/HTTPS URL")
        return v


# ── Output ─────────────────────────────────────────────────────────────────────

class ParticipantOut(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class TranscriptOut(BaseModel):
    id: uuid.UUID
    content_raw: Optional[str] = None
    content_translated: Optional[str] = None
    primary_language: Optional[str] = None
    file_url: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptChunkOut(BaseModel):
    id: uuid.UUID
    speaker: Optional[str] = None
    text: str
    language: Optional[str] = None
    start_time: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str] = None
    platform: str
    meeting_url: str
    recall_bot_id: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    participants: List[ParticipantOut] = []
    transcript: Optional[TranscriptOut] = None

    model_config = {"from_attributes": True}


class MeetingListItem(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    platform: str
    status: str
    meeting_url: str
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
