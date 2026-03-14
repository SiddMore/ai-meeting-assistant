"""
email.py — Celery tasks for email dispatch (queue: email).
"""
import logging
import uuid
import asyncio
from typing import Dict, Any

from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models.mom import MOM
from app.db.models.meeting import Meeting
from app.db.models.action_item import ActionItem
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

log = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.email.send_mom_email_task")
def send_mom_email_task(self, mom_id: str) -> Dict[str, Any]:
    """
    Celery task: fetch the MOM from DB and send the email to all participants.

    Args:
        mom_id: UUID string of the MOM record.

    Returns:
        Dict with status information.
    """
    try:
        result = asyncio.run(_send_mom_email(mom_id))
        return result
    except Exception as exc:
        log.error("send_mom_email_task failed for %s: %s", mom_id, exc, exc_info=True)
        raise self.retry(countdown=60, max_retries=3)


async def _send_mom_email(mom_id: str) -> Dict[str, Any]:
    """Async core: load MOM + meeting + action items and call email_service."""
    from app.services.email_service import send_mom_email as _send

    mom_uuid = uuid.UUID(mom_id)

    async with AsyncSessionLocal() as db:
        # Load MOM with related meeting and action items
        result = await db.execute(
            select(MOM)
            .options(
                selectinload(MOM.meeting).selectinload(Meeting.participants),
                selectinload(MOM.action_items),
            )
            .where(MOM.id == mom_uuid)
        )
        mom = result.scalar_one_or_none()

        if not mom:
            raise ValueError(f"MOM {mom_id} not found")

        meeting = mom.meeting
        if not meeting:
            raise ValueError(f"Meeting for MOM {mom_id} not found")

        # Collect recipient e-mails: participants + meeting owner's email
        participant_emails: list[str] = [
            p.email for p in meeting.participants if p.email
        ]
        # Also load the meeting owner's email
        from app.db.models.user import User
        user_result = await db.execute(
            select(User).where(User.id == meeting.user_id)
        )
        owner = user_result.scalar_one_or_none()
        if owner and owner.email and owner.email not in participant_emails:
            participant_emails.append(owner.email)

        if not participant_emails:
            log.warning("No recipient emails found for MOM %s — skipping send", mom_id)
            return {"status": "skipped", "reason": "no_recipients"}

        participants_payload = [
            {"name": p.name, "email": p.email}
            for p in meeting.participants
        ]

        action_items_payload = [
            {
                "task": ai.task,
                "assignee_name": ai.assignee_name,
                "assignee_email": ai.assignee_email,
                "deadline": str(ai.deadline) if ai.deadline else None,
                "priority": ai.priority.value if hasattr(ai.priority, "value") else str(ai.priority),
            }
            for ai in mom.action_items
        ]

        send_result = await _send(
            mom_id=str(mom.id),
            meeting_title=meeting.title or "Untitled Meeting",
            meeting_date=meeting.ended_at or meeting.started_at or datetime.utcnow(),
            participants=participants_payload,
            summary=mom.summary,
            key_decisions=mom.key_decisions,
            action_items=action_items_payload,
            to_emails=participant_emails,
        )

        # Mark MOM as sent
        mom.email_sent = True
        mom.sent_at = datetime.utcnow()
        await db.commit()

        log.info("MOM email dispatched for %s. Status: %s", mom_id, send_result.get("status"))
        return send_result
