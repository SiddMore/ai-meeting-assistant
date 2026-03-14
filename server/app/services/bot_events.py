"""
bot_events.py — normalize bot lifecycle + transcript ingestion.

This module provides a single event-processing path used by:
- Recall.ai webhooks (HTTP)
- Custom/self-hosted bot ingestion (HTTP / Socket.IO)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.transcript_chunk import TranscriptChunk
from app.realtime.socketio_server import emit_meeting_event

BotEventType = Literal[
    "bot.joining_call",
    "bot.in_call_not_recording",
    "bot.in_call_recording",
    "transcript.data",
    "bot.done",
    "bot.fatal_error",
]


async def get_meeting_by_bot_id(db: AsyncSession, bot_id: str) -> Meeting | None:
    result = await db.execute(select(Meeting).where(Meeting.recall_bot_id == bot_id))
    return result.scalar_one_or_none()


async def process_bot_event(
    *,
    db: AsyncSession,
    meeting: Meeting,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply an incoming event to DB state and emit realtime updates.

    Returns a small dict with {status, ...} for HTTP responses.
    """
    meeting_id = str(meeting.id)

    # ── Bot joined ─────────────────────────────────────────────────────────────
    if event_type in ("bot.joining_call", "bot.in_call_not_recording"):
        meeting.status = MeetingStatus.bot_joining
        await db.commit()
        await emit_meeting_event(
            meeting_id,
            "meeting.status",
            {"meeting_id": meeting_id, "status": "bot_joining"},
        )
        return {"status": "ok", "event": event_type}

    # ── Bot recording ──────────────────────────────────────────────────────────
    if event_type == "bot.in_call_recording":
        meeting.status = MeetingStatus.in_progress
        meeting.started_at = datetime.now(timezone.utc)
        await db.commit()
        await emit_meeting_event(
            meeting_id,
            "meeting.status",
            {"meeting_id": meeting_id, "status": "in_progress", "started_at": meeting.started_at.isoformat()},
        )
        return {"status": "ok", "event": event_type}

    # ── Live transcript chunk ──────────────────────────────────────────────────
    if event_type == "transcript.data":
        data = payload.get("data", {}) or {}
        text = str(data.get("text", "")).strip()
        if not text:
            return {"status": "ignored", "reason": "empty transcript"}

        chunk = TranscriptChunk(
            meeting_id=meeting.id,
            speaker=data.get("speaker"),
            text=text,
            language=data.get("language", "en"),
            start_time=data.get("start_time"),
            is_final=bool(data.get("is_final", True)),
        )
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)

        await emit_meeting_event(
            meeting_id,
            "transcript.chunk",
            {
                "meeting_id": meeting_id,
                "chunk_id": str(chunk.id),
                "speaker": chunk.speaker,
                "text": chunk.text,
                "language": chunk.language,
                "start_time": chunk.start_time,
                "is_final": chunk.is_final,
                "created_at": chunk.created_at.isoformat(),
            },
        )
        return {"status": "ok", "event": event_type, "chunk_id": str(chunk.id)}

    # ── Bot left / done ────────────────────────────────────────────────────────
    if event_type == "bot.done":
        meeting.status = MeetingStatus.processing
        meeting.ended_at = datetime.now(timezone.utc)
        await db.commit()
        await emit_meeting_event(
            meeting_id,
            "meeting.status",
            {"meeting_id": meeting_id, "status": "processing", "ended_at": meeting.ended_at.isoformat()},
        )
        
        # Trigger MOM generation (Phase 4)
        from app.workers.mom import generate_mom_task
        generate_mom_task.delay(str(meeting.id))
        
        return {"status": "ok", "event": event_type}

    # ── Bot error ──────────────────────────────────────────────────────────────
    if event_type == "bot.fatal_error":
        meeting.status = MeetingStatus.failed
        await db.commit()
        await emit_meeting_event(
            meeting_id,
            "meeting.status",
            {"meeting_id": meeting_id, "status": "failed", "error": payload.get("error", "Unknown bot error")},
        )
        return {"status": "ok", "event": event_type}

    return {"status": "ignored", "reason": f"unhandled event: {event_type}"}

