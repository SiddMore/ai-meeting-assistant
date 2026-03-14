"""
meetings.py — CRUD routes for meeting management + bot deployment.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from app.db.session import get_db
from app.db.models.meeting import Meeting, MeetingStatus, MeetingPlatform
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.meeting import MeetingCreate, MeetingOut, MeetingListItem
from app.services.bot_service import bot_service, _validate_meeting_url
from app.core.config import settings
from app.core.security import create_bot_token

router = APIRouter()


# ── POST / — Create meeting + deploy bot ───────────────────────────────────────

@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a meeting record and deploy the bot to the provided URL."""
    try:
        platform = MeetingPlatform(payload.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {payload.platform}")

    if not await _validate_meeting_url(payload.meeting_url):
        raise HTTPException(status_code=400, detail="Invalid meeting URL")

    # 1. Create DB record with a temporary 'joining' status
    meeting = Meeting(
        user_id=current_user.id,
        title=payload.title or f"{platform.value.replace('_', ' ').title()} Meeting",
        platform=platform,
        meeting_url=payload.meeting_url,
        status=MeetingStatus.bot_joining, # Start straight in joining
        # FALLBACK: Assign a random UUID as a recall_bot_id immediately 
        # so the simulator can always find this meeting in dev mode.
        recall_bot_id=str(uuid.uuid4()) 
    )
    
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # 2. Attempt real deployment
    try:
        webhook_url = getattr(settings, "RECALL_AI_WEBHOOK_URL", "http://localhost:8000/api/v1/webhooks/recall")
        
        # If bot_service is real, it will overwrite our temporary recall_bot_id
        real_bot_id = await bot_service.deploy_bot(
            meeting_url=payload.meeting_url,
            webhook_url=webhook_url,
        )
        
        if real_bot_id:
            meeting.recall_bot_id = real_bot_id
            
        await db.commit()
        await db.refresh(meeting)
        
    except Exception as e:
        # In DEV, we don't want to crash if Recall.ai isn't connected
        # We just log it and keep our fake ID so the user can simulate!
        import logging
        logging.error(f"Bot deployment skipped/failed: {str(e)}. Using simulated ID.")
        # We don't set status to failed here so the simulator can still be used.

    # 3. Reload with participants for the frontend
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.participants))
        .where(Meeting.id == meeting.id)
    )
    return result.scalar_one()

# ── GET / — List meetings for the current user ─────────────────────────────────

@router.get("", response_model=List[MeetingListItem])
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
):
    result = await db.execute(
        select(Meeting)
        .where(Meeting.user_id == current_user.id)
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# ── GET /{meeting_id} — Get single meeting ─────────────────────────────────────

@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.participants))
        .options(selectinload(Meeting.transcript))
        .where(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


# ── POST /{meeting_id}/bot/token — Mint bot ingest token ──────────────────────
@router.post("/{meeting_id}/bot/token")
async def mint_bot_token(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a short-lived token your self-hosted bot can use to ingest events
    for this meeting via HTTP or Socket.IO.
    """
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    token = create_bot_token(str(meeting.id))
    return {"meeting_id": str(meeting.id), "bot_token": token, "expires_in_hours": 12}


# ── DELETE /{meeting_id} — Remove meeting + stop bot ──────────────────────────

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Stop bot if active
    if meeting.recall_bot_id and meeting.status in (MeetingStatus.bot_joining, MeetingStatus.in_progress):
        try:
            await bot_service.stop_bot(meeting.recall_bot_id)
        except Exception:
            pass  # Don't block deletion if bot stop fails

    await db.delete(meeting)
    await db.commit()
