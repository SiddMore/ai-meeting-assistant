import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.action_item import ActionItem
from app.db.models.calendar_event import CalendarEvent, CalendarProvider
from app.db.models.mom import MOM
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.services import calendar_google, calendar_microsoft


log = logging.getLogger(__name__)


async def _get_owner_for_action_item(db: AsyncSession, action_item: ActionItem) -> User | None:
    """
    Load the owning user for an action item via its MOM/Meeting relationship.
    """
    if action_item.mom and action_item.mom.meeting and action_item.mom.meeting.owner:
        return action_item.mom.meeting.owner

    stmt = (
        select(User)
        .join(Meeting, Meeting.user_id == User.id)
        .join(MOM, MOM.meeting_id == Meeting.id)
        .where(MOM.id == action_item.mom_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _pick_provider(user: User) -> CalendarProvider | None:
    """
    Decide which calendar provider to use for a user.
    Preference order: Google, then Microsoft.
    """
    if user.google_refresh_token_enc:
        return CalendarProvider.google
    if user.microsoft_refresh_token_enc:
        return CalendarProvider.microsoft
    return None


async def create_event(db: AsyncSession, action_item: ActionItem) -> None:
    """
    Create or update a CalendarEvent row and push an event to the external
    provider if the user has a connected calendar.
    """
    owner = await _get_owner_for_action_item(db, action_item)
    if not owner:
        log.info("No owner found for action_item=%s; skipping calendar sync", action_item.id)
        return

    provider = _pick_provider(owner)
    if not provider:
        log.info("User %s has no connected calendar provider; skipping sync", owner.id)
        return

    # Ensure CalendarEvent row exists
    calendar_event = action_item.calendar_event
    if not calendar_event:
        calendar_event = CalendarEvent(
            action_item_id=action_item.id,
            provider=provider,
            synced=False,
        )
        db.add(calendar_event)
        await db.flush()
    else:
        calendar_event.provider = provider

    # Delegate to provider service
    if provider == CalendarProvider.google:
        event_id, url = await calendar_google.create_event(owner, action_item)
    else:
        event_id, url = await calendar_microsoft.create_event(owner, action_item)

    if not event_id:
        log.warning("Failed to create external event for action_item=%s", action_item.id)
        return

    calendar_event.external_event_id = event_id
    calendar_event.event_url = url
    calendar_event.synced = True
    calendar_event.synced_at = datetime.utcnow()
    await db.commit()


async def update_event(db: AsyncSession, action_item: ActionItem) -> None:
    """
    Update an existing calendar event when the action item changes.
    """
    owner = await _get_owner_for_action_item(db, action_item)
    if not owner:
        return

    calendar_event = action_item.calendar_event
    if not calendar_event or not calendar_event.external_event_id:
        # Nothing to update yet; try creating instead
        await create_event(db, action_item)
        return

    provider = calendar_event.provider

    if provider == CalendarProvider.google:
        await calendar_google.update_event(owner, calendar_event, action_item)
    elif provider == CalendarProvider.microsoft:
        await calendar_microsoft.update_event(owner, calendar_event, action_item)

    calendar_event.synced = True
    calendar_event.synced_at = datetime.utcnow()
    await db.commit()


async def delete_event(db: AsyncSession, action_item: ActionItem) -> None:
    """
    Delete the external calendar event (if any) when an action item is deleted.
    """
    owner = await _get_owner_for_action_item(db, action_item)
    if not owner:
        return

    calendar_event = action_item.calendar_event
    if not calendar_event:
        return

    if calendar_event.provider == CalendarProvider.google:
        await calendar_google.delete_event(owner, calendar_event)
    elif calendar_event.provider == CalendarProvider.microsoft:
        await calendar_microsoft.delete_event(owner, calendar_event)

    await db.delete(calendar_event)
    await db.commit()

