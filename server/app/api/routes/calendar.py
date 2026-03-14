from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.action_item import ActionItem
from app.db.models.calendar_event import CalendarEvent
from app.db.models.mom import MOM
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.calendar import (
    CalendarIntegrationStatus,
    CalendarEventOut,
    CalendarEventsResponse,
)


# Two routers so main.py can mount them at the correct prefixes independently:
#   integrations_router -> /api/v1   (paths already contain /integrations/...)
#   calendar_router     -> /api/v1   (paths already contain /calendar/...)
integrations_router = APIRouter()
calendar_router = APIRouter()

# Backwards-compat alias (used by tests that import `router`)
router = calendar_router


@integrations_router.get("/integrations/calendar", response_model=List[CalendarIntegrationStatus])
async def get_calendar_integrations(
    current_user: User = Depends(get_current_user),
) -> List[CalendarIntegrationStatus]:
    """
    Return which calendar providers are connected for the current user.
    """
    providers: List[CalendarIntegrationStatus] = []

    providers.append(
        CalendarIntegrationStatus(
            provider="google",
            connected=bool(current_user.google_refresh_token_enc),
            has_calendar_scopes=bool(current_user.google_refresh_token_enc),
        )
    )
    providers.append(
        CalendarIntegrationStatus(
            provider="microsoft",
            connected=bool(current_user.microsoft_refresh_token_enc),
            has_calendar_scopes=bool(current_user.microsoft_refresh_token_enc),
        )
    )

    return providers


@integrations_router.post("/integrations/calendar/{provider}/disconnect")
async def disconnect_calendar_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect Google or Microsoft calendar by clearing stored refresh tokens.
    """
    changed = False
    if provider == "google":
        if current_user.google_refresh_token_enc:
            current_user.google_refresh_token_enc = None
            changed = True
    elif provider == "microsoft":
        if current_user.microsoft_refresh_token_enc:
            current_user.microsoft_refresh_token_enc = None
            changed = True
    else:
        # Unknown provider; no-op
        return {"status": "ignored", "provider": provider}

    if changed:
        await db.commit()

    return {"status": "disconnected", "provider": provider}


@calendar_router.get("/calendar/events", response_model=CalendarEventsResponse)
async def list_calendar_events(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarEventsResponse:
    """
    Return events derived from ActionItems for the current user within a date range.
    This does NOT fetch from external calendars; it derives from our DB only.
    """
    # Default range: +/- 30 days from today if not provided
    now = datetime.utcnow()
    if not start:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if not end:
        end = start.replace(hour=23, minute=59, second=59, microsecond=0)

    # Join ActionItem -> MOM -> Meeting -> User
    stmt = (
        select(ActionItem, MOM, Meeting, CalendarEvent)
        .join(MOM, ActionItem.mom_id == MOM.id)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .outerjoin(CalendarEvent, CalendarEvent.action_item_id == ActionItem.id)
        .where(Meeting.user_id == current_user.id)
    )

    results = await db.execute(stmt)
    rows = results.all()

    items: List[CalendarEventOut] = []
    for action_item, mom, meeting, cal_event in rows:
        # Filter by provider if requested
        effective_provider = "none"
        if cal_event and cal_event.provider:
            effective_provider = cal_event.provider.value
        if provider and provider != effective_provider:
            continue

        # Filter by status if requested
        if status and action_item.status.value != status:
            continue

        # Map deadline to event window
        if action_item.deadline:
            d: date = action_item.deadline
            ev_start = datetime(d.year, d.month, d.day, 9, 0)
            ev_end = datetime(d.year, d.month, d.day, 10, 0)
        else:
            # Fallback to meeting start time or created_at
            base = meeting.started_at or meeting.created_at
            ev_start = base
            ev_end = base + (end - start)

        if ev_end < start or ev_start > end:
            continue

        items.append(
            CalendarEventOut(
                id=str(action_item.id),
                title=action_item.task,
                start=ev_start,
                end=ev_end,
                provider=effective_provider,  # type: ignore[arg-type]
                status=action_item.status.value,  # type: ignore[arg-type]
                priority=action_item.priority.value,  # type: ignore[arg-type]
                mom_id=str(mom.id) if mom else None,
                action_item_id=str(action_item.id),
            )
        )

    return CalendarEventsResponse(events=items)

