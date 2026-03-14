"""
simulate.py — Dev-only routes. Security bypass added for easier testing.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.db.session import get_db
from app.db.models.meeting import Meeting, MeetingStatus
# User aur get_current_user ki abhi zaroorat nahi simulation mein
from app.db.models.user import User

router = APIRouter()

_INTERNAL_WEBHOOK = "http://127.0.0.1:8000/api/v1/webhooks/recall"

async def _fire_event(bot_id: str, event: str, extra: dict = {}):
    payload = {"bot_id": bot_id, "event": event, **extra}
    async with httpx.AsyncClient() as client:
        # 127.0.0.1 use karna safe hai local dev ke liye
        await client.post(_INTERNAL_WEBHOOK, json=payload, timeout=10)

async def _get_meeting_no_auth(meeting_id: uuid.UUID, db: AsyncSession) -> Meeting:
    """Security bypass: Finds meeting by ID only, ignoring user_id for simulation."""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.recall_bot_id:
        # Agar ye error aaye, toh DB mein recall_bot_id manually daal dena (e.g. 'mock-123')
        raise HTTPException(status_code=400, detail="Meeting has no bot attached yet")
    return meeting

@router.post("/{meeting_id}/start")
async def simulate_start(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    meeting = await _get_meeting_no_auth(meeting_id, db)
    await _fire_event(meeting.recall_bot_id, "bot.joining_call")
    await _fire_event(meeting.recall_bot_id, "bot.in_call_recording")
    return {"status": "ok", "msg": "Bot started recording"}

@router.post("/{meeting_id}/chunk")
async def simulate_chunk(
    meeting_id: uuid.UUID,
    text: str = Body(..., embed=True),
    speaker: Optional[str] = Body(default="Speaker 1", embed=True),
    db: AsyncSession = Depends(get_db)
):
    meeting = await _get_meeting_no_auth(meeting_id, db)
    await _fire_event(meeting.recall_bot_id, "transcript.data", {
        "data": {
            "text": text,
            "speaker": speaker,
            "is_final": True,
        }
    })
    return {"status": "ok", "text": text}

@router.post("/{meeting_id}/end")
async def simulate_end(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    meeting = await _get_meeting_no_auth(meeting_id, db)
    
    from app.db.models.meeting import MeetingStatus
    from datetime import datetime
    import uuid
    from sqlalchemy import text
    
    # 1. Force status to COMPLETED so Next.js unlocks the page immediately!
    meeting.status = MeetingStatus.completed
    meeting.ended_at = datetime.utcnow()
    await db.commit()
    
    # 2. HACKATHON GOD MODE: Inject a realistic MOM directly via raw SQL
    mock_summary = "The team discussed the upcoming TechRush hackathon deployment. Siddhi will handle the final database cleanup and deployment tomorrow."
    mock_decisions = "- TechRush deployment scheduled for tomorrow.\n- Database must be wiped clean before the presentation."
    mock_content = "# Minutes of Meeting: TechRush Sync\n\n## Summary\nThe team discussed the upcoming TechRush hackathon deployment. Siddhi is taking the lead on the final backend checks.\n\n## Key Decisions\n- Deployment scheduled for tomorrow.\n- Database clean slate confirmed.\n\n## Action Items\n- Clean database (Assignee: Siddhi, Priority: High)\n- Deploy application (Assignee: Siddhi, Priority: High)"
    
    try:
        await db.execute(text("""
            INSERT INTO moms (id, meeting_id, summary, key_decisions, full_content, email_sent, created_at)
            VALUES (:id, :m_id, :sum, :kd, :fc, false, :now)
            ON CONFLICT (meeting_id) DO NOTHING
        """), {
            "id": uuid.uuid4(),
            "m_id": meeting.id,
            "sum": mock_summary,
            "kd": mock_decisions,
            "fc": mock_content,
            "now": datetime.utcnow()
        })
        await db.commit()
        print("✅ GOD MODE: MOM INJECTED PERFECTLY!")
    except Exception as e:
        print(f"❌ INJECTION ERROR: {e}")
        
    return {"status": "ok", "msg": "Hackathon God Mode Executed!"}