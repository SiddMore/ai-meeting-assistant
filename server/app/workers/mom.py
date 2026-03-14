"""
mom.py — Celery tasks for MOM (Minutes of Meeting) generation.
"""
import logging
import uuid
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models.mom import MOM
from app.db.models.action_item import ActionItem, TaskPriority
from app.db.models.meeting import Meeting, MeetingStatus
from app.services.mom_service import generate_mom
from app.realtime.socketio_server import emit_meeting_event

log = logging.getLogger(__name__)

@celery_app.task(bind=True, name="app.workers.mom.generate_mom")
def generate_mom_task(self, meeting_id: str) -> Dict[str, Any]:
    try:
        asyncio.run(_generate_mom_for_meeting(meeting_id))
        return {"status": "completed", "meeting_id": meeting_id}
    except Exception as e:
        log.error(f"Failed to generate MOM for {meeting_id}: {e}", exc_info=True)
        raise self.retry(countdown=60, max_retries=3)

async def _generate_mom_for_meeting(meeting_id: str):
    meeting_uuid = uuid.UUID(meeting_id)

    async with AsyncSessionLocal() as db:
        # 1. Fetch meeting with transcript
        result = await db.execute(
            select(Meeting).options(joinedload(Meeting.transcript)).where(Meeting.id == meeting_uuid)
        )
        meeting = result.scalar_one_or_none()

        if not meeting:
            return

        # 2. Get transcript text
        transcript_content = ""
        if meeting.transcript:
            transcript_content = meeting.transcript.content_translated or meeting.transcript.content_raw or ""

        if not transcript_content.strip():
            transcript_content = "No discussion recorded."

        # 3. Generate MOM using Gemini
        mom_data = await generate_mom(
            meeting_title=meeting.title or "Untitled Meeting",
            transcript_text=transcript_content,
            participants=meeting.participants or [],
            meeting_date=meeting.ended_at or datetime.now(timezone.utc)
        )

        # 4. Save MOM to Database
        mom = MOM(
            meeting_id=meeting_uuid,
            summary=mom_data["summary"],
            key_decisions=mom_data["key_decisions"],
            full_content=mom_data["full_content"]
        )
        db.add(mom)
        await db.flush()

        # 5. Save Action Items
        for item in mom_data.get("action_items", []):
            db.add(ActionItem(
                mom_id=mom.id,
                task=item["task"],
                assignee_name=item.get("assignee_name"),
                priority=TaskPriority(item.get("priority", "medium"))
            ))

        # 6. Mark Meeting as Completed
        meeting.status = MeetingStatus.completed
        await db.commit()

        # 7. Notify Frontend
        await emit_meeting_event(
            meeting_id,
            "meeting.status",
            {"meeting_id": meeting_id, "status": "completed"}
        )
        log.info(f"✅ Successfully finalized meeting {meeting_id}")