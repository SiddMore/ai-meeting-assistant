"""
transcripts.py — Endpoints for retrieving meeting transcripts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.db.models.meeting import Meeting
from app.db.models.transcript_chunk import TranscriptChunk
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.meeting import TranscriptChunkOut

router = APIRouter()


@router.get("/{meeting_id}", response_model=List[TranscriptChunkOut])
async def get_transcript(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all transcript chunks for a meeting (ordered by time)."""
    # Verify the meeting belongs to the current user
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    chunks_result = await db.execute(
        select(TranscriptChunk)
        .where(TranscriptChunk.meeting_id == meeting_id)
        .order_by(TranscriptChunk.start_time.asc().nullslast(), TranscriptChunk.created_at.asc())
    )
    return chunks_result.scalars().all()
