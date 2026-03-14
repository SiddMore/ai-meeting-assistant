"""
socketio_server.py — Socket.IO realtime server (FastAPI + python-socketio).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import socketio

# Configuration imports
if os.environ.get('TESTING'):
    from app.core.test_config import settings
    from app.services.redis_buffer_service import RedisBufferService
else:
    from app.core.config import settings
    from app.services.redis_buffer_service import RedisBufferService

log = logging.getLogger(__name__)

def _meeting_room(meeting_id: str) -> str:
    return f"meeting:{meeting_id}"

# ── Server Initialization ─────────────────────────────────────────────────────

def create_sio_server() -> socketio.AsyncServer:
    return socketio.AsyncServer(
        async_mode="asgi",
        # FIX: Exact match for Next.js (No wildcard '*')
        cors_allowed_origins=[
            "http://localhost:3000", 
            "http://127.0.0.1:3000"
        ], 
        logger=True,
        engineio_logger=True,
        ping_interval=10,
        ping_timeout=20,
        max_http_buffer_size=10 * 1024 * 1024,
    )

sio = create_sio_server()

# Global state
_sid_meta: dict[str, dict[str, Any]] = {}
redis_buffer_service = RedisBufferService()

# ── Helper Functions ──────────────────────────────────────────────────────────

async def emit_meeting_event(meeting_id: str, event: str, data: dict[str, Any]) -> None:
    try:
        await sio.emit(event, data, room=_meeting_room(meeting_id))
    except Exception as exc:
        log.warning("socket emit failed (meeting_id=%s event=%s): %s", meeting_id, event, exc)

async def _load_meeting_snapshot(meeting_id: str, user_id: str) -> dict[str, Any] | None:
    try:
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.db.models.meeting import Meeting
        from app.db.models.transcript_chunk import TranscriptChunk

        async with AsyncSessionLocal() as db:
            meeting_uuid = uuid.UUID(meeting_id)
            user_uuid = uuid.UUID(user_id)
            
            meeting_res = await db.execute(
                select(Meeting).where(Meeting.id == meeting_uuid, Meeting.user_id == user_uuid)
            )
            meeting = meeting_res.scalar_one_or_none()
            if not meeting: return None

            chunks_res = await db.execute(
                select(TranscriptChunk)
                .where(TranscriptChunk.meeting_id == meeting_uuid)
                .order_by(TranscriptChunk.created_at.asc())
                .limit(50)
            )
            chunks = chunks_res.scalars().all()
            buffer_status = await redis_buffer_service.get_buffer_status(meeting_id)

            return {
                "meeting": {
                    "id": str(meeting.id),
                    "status": str(meeting.status.value),
                },
                "recent_chunks": [
                    {"chunk_id": str(c.id), "speaker": c.speaker, "text": c.text}
                    for c in chunks
                ],
                "buffer_status": buffer_status,
            }
    except Exception as exc:
        log.warning("snapshot load failed: %s", exc)
        return None

async def _verify_access_token(token: str) -> str | None:
    try:
        from app.core.security import verify_token
        payload = await verify_token(token, token_type="access")
        return payload.get("sub")
    except Exception: return None

async def _verify_bot_token(token: str) -> str | None:
    try:
        from app.core.security import verify_token
        payload = await verify_token(token, token_type="bot")
        return payload.get("meeting_id")
    except Exception: return None

# ── Core Socket Events ────────────────────────────────────────────────────────

@sio.event
async def connect(sid, environ, auth=None):
    print(f"🔌 Socket connected: {sid}")
    _sid_meta[sid] = {
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "auth": auth or {},
    }

@sio.event
async def disconnect(sid):
    print(f"🔌 Socket disconnected: {sid}")
    _sid_meta.pop(sid, None)

@sio.event
async def join_meeting(sid, data):
    meeting_id = (data or {}).get("meeting_id")
    token = (data or {}).get("token")
    if not meeting_id: return {"ok": False, "error": "meeting_id required"}

    user_id = await _verify_access_token(token) if token else None
    await sio.enter_room(sid, _meeting_room(meeting_id))
    
    if user_id:
        snap = await _load_meeting_snapshot(meeting_id, user_id)
        if snap: await sio.emit("meeting.snapshot", snap, to=sid)

    return {"ok": True, "meeting_id": meeting_id}

# ── Bot Streaming Events ──────────────────────────────────────────────────────

@sio.on("bot_transcript_chunk")
async def handle_bot_chunk(sid, data):
    try:
        bot_token = data.get("bot_token")
        meeting_id = await _verify_bot_token(bot_token)
        if not meeting_id: return {"ok": False, "error": "unauthorized"}

        transcript_data = data.get("data", {})
        chunk = transcript_data.get("chunk")

        if chunk:
            # Broadcast to the meeting room room
            await sio.emit("transcript.data", {
                "meeting_id": meeting_id,
                "chunk": chunk
            }, room=_meeting_room(meeting_id))
            
            # Save to Redis for catch-up
            await redis_buffer_service.add_chunk_to_buffer(meeting_id, chunk)

        return {"ok": True}
    except Exception as e:
        log.error(f"Error in bot_chunk: {e}")
        return {"ok": False}

@sio.on("bot_done")
async def handle_bot_done(sid, data):
    bot_token = data.get("bot_token")
    meeting_id = await _verify_bot_token(bot_token)
    if meeting_id:
        await redis_buffer_service.clear_buffer(meeting_id)
        await sio.emit("meeting.completed", {"meeting_id": meeting_id}, room=_meeting_room(meeting_id))
    return {"ok": True}