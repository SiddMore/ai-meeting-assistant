"""
webhooks.py — Handles incoming bot lifecycle events (Recall.ai or mock simulation).

This is intentionally resilient:
- Invalid payloads are rejected with clear 4xx errors
- Downstream realtime emits must never crash ingestion
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.db.session import AsyncSessionLocal
from app.services.bot_events import get_meeting_by_bot_id, process_bot_event

router = APIRouter()


@router.post("/recall")
async def recall_webhook(request: Request):
    """
    Unified webhook endpoint for Recall.ai bot events (and mock simulation).
    Each event carries a `bot_id` and an `event` type.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type: str = payload.get("event", "") or ""
    bot_id: str = payload.get("bot_id", "") or ""

    if not bot_id:
        return JSONResponse({"status": "ignored", "reason": "no bot_id"})

    async with AsyncSessionLocal() as db:
        meeting = await get_meeting_by_bot_id(db, bot_id)
        if not meeting:
            return JSONResponse({"status": "ignored", "reason": "unknown bot_id"})
        result = await process_bot_event(db=db, meeting=meeting, event_type=event_type, payload=payload)
        return JSONResponse(result)
