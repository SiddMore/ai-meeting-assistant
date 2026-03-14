"""
calendar_sync.py — Celery tasks for syncing ActionItems to external calendars.
"""
import logging
import uuid

from celery import shared_task
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models.action_item import ActionItem
from app.services import calendar_service


log = logging.getLogger(__name__)


@shared_task(name="app.workers.calendar_sync.create_or_update")
def sync_action_item_to_calendar(action_item_id: str) -> None:
    """
    Create an external calendar event for the given ActionItem (or update if it
    already exists).
    """
    try:
        uuid_obj = uuid.UUID(action_item_id)
    except ValueError:
        log.error("Invalid action_item_id passed to calendar sync: %s", action_item_id)
        return

    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ActionItem).where(ActionItem.id == uuid_obj))
            action_item = result.scalar_one_or_none()
            if not action_item:
                log.warning("ActionItem %s not found; skipping calendar sync", action_item_id)
                return
            await calendar_service.create_event(db, action_item)

    import asyncio

    asyncio.run(_run())


@shared_task(name="app.workers.calendar_sync.update")
def update_action_item_calendar_event(action_item_id: str) -> None:
    """Update an existing external event when the ActionItem is modified."""
    try:
        uuid_obj = uuid.UUID(action_item_id)
    except ValueError:
        log.error("Invalid action_item_id passed to calendar update: %s", action_item_id)
        return

    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ActionItem).where(ActionItem.id == uuid_obj))
            action_item = result.scalar_one_or_none()
            if not action_item:
                log.warning("ActionItem %s not found; skipping calendar update", action_item_id)
                return
            await calendar_service.update_event(db, action_item)

    import asyncio

    asyncio.run(_run())


@shared_task(name="app.workers.calendar_sync.delete")
def delete_action_item_calendar_event(action_item_id: str) -> None:
    """Delete the external event when an ActionItem is deleted."""
    try:
        uuid_obj = uuid.UUID(action_item_id)
    except ValueError:
        log.error("Invalid action_item_id passed to calendar delete: %s", action_item_id)
        return

    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ActionItem).where(ActionItem.id == uuid_obj))
            action_item = result.scalar_one_or_none()
            if not action_item:
                log.info("ActionItem %s already gone; nothing to delete", action_item_id)
                return
            await calendar_service.delete_event(db, action_item)

    import asyncio

    asyncio.run(_run())

