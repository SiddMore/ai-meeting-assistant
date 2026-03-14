"""
catch_me_up.py — API endpoint for real-time transcript catch-up functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import datetime

from app.db.session import get_db
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.meeting import TranscriptChunkOut
from app.utils.redis_client import get_redis

router = APIRouter()


class TranscriptChunkOut(TranscriptChunkOut):
    """Extend the existing schema with additional fields."""
    class Config:
        from_attributes = True


class CatchMeUpResponse(BaseModel):
    meeting_id: uuid.UUID
    chunks: List[TranscriptChunkOut]
    total_chunks: int
    buffer_size: int
    timestamp: datetime.datetime


@router.get("/{meeting_id}", response_model=CatchMeUpResponse)
async def catch_me_up(
    meeting_id: uuid.UUID,
    chunk_count: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return recent transcript chunks from Redis buffer with real-time streaming support.
    
    Features:
    - Returns recent transcript chunks from Redis buffer
    - Configurable chunk count (default 100)
    - Real-time streaming support for continuous updates
    - Authentication and meeting ownership validation
    - Error handling for missing meetings or buffer issues
    
    Response schema:
    - meeting_id: str
    - chunks: List[TranscriptChunkOut]
    - total_chunks: int
    - buffer_size: int
    - timestamp: datetime
    """
    # Verify the meeting belongs to the current user
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found or access denied")

    # Get Redis client
    redis_client = get_redis()

    try:
        # Get buffer size
        buffer_key = f"transcript_buffer:{meeting_id}"
        buffer_size = await redis_client.llen(buffer_key)
        
        # Get recent chunks (from the end of the list)
        start = max(0, buffer_size - chunk_count)
        end = -1
        
        raw_chunks = await redis_client.lrange(buffer_key, start, end)
        
        # Parse chunks (assuming they're stored as JSON strings)
        chunks = []
        for chunk_data in raw_chunks:
            try:
                chunk = TranscriptChunkOut.parse_raw(chunk_data)
                chunks.append(chunk)
            except Exception:
                continue  # Skip malformed chunks
        
        # Get total chunks from database (for completeness)
        chunks_result = await db.execute(
            select(TranscriptChunk)
            .where(TranscriptChunk.meeting_id == meeting_id)
            .order_by(TranscriptChunk.created_at.asc())
        )
        total_chunks = chunks_result.rowcount
        
        return CatchMeUpResponse(
            meeting_id=meeting_id,
            chunks=chunks,
            total_chunks=total_chunks,
            buffer_size=buffer_size,
            timestamp=datetime.datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error accessing transcript buffer: {str(e)}"
        )