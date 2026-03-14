"""
bot_ingest.py — endpoints for a self-hosted/custom meeting bot.

Your bot can:
- send lifecycle events (joining/recording/done/error)
- send transcript chunks

Auth:
- Requires a **bot token** minted from `POST /api/v1/meetings/{meeting_id}/bot/token`
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.security import verify_token
from app.db.session import AsyncSessionLocal
from app.db.models.meeting import Meeting
from app.services.bot_events import process_bot_event

router = APIRouter()


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <bot_token>")


@router.post("/meetings/{meeting_id}/event")
async def ingest_event(meeting_id: uuid.UUID, request: Request):
    """
    Ingest a bot event for a meeting.

    Body schema (Recall-compatible):
    {
      "event": "transcript.data" | "bot.joining_call" | ...,
      "data": { ... },     // only for transcript.data
      "error": "..."       // only for bot.fatal_error
    }
    """
    token = _extract_bearer_token(request)
    payload = await verify_token(token, token_type="bot")
    token_meeting_id = payload.get("meeting_id")
    if token_meeting_id != str(meeting_id):
        raise HTTPException(status_code=403, detail="Bot token not valid for this meeting")

    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = str(body.get("event", "") or "")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event")

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = res.scalar_one_or_none()
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        result = await process_bot_event(db=db, meeting=meeting, event_type=event_type, payload=body)
        return JSONResponse(result)

