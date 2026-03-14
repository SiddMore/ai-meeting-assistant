import logging
from datetime import datetime, timedelta, date
from typing import Tuple

import httpx

from app.core.config import settings
from app.db.models.action_item import ActionItem
from app.db.models.calendar_event import CalendarEvent, CalendarProvider
from app.db.models.user import User
from app.services.auth_service import decrypt_token


log = logging.getLogger(__name__)

GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


async def _get_google_access_token(user: User) -> str | None:
    """
    Exchange the stored Google refresh token for a short‑lived access token.
    Returns None if the user is not connected or configuration is incomplete.
    """
    if not user.google_refresh_token_enc:
        return None
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        log.warning("Google OAuth credentials not configured; skipping calendar sync")
        return None

    refresh_token = decrypt_token(user.google_refresh_token_enc)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if resp.status_code != 200:
            log.error("Failed to refresh Google access token: %s %s", resp.status_code, resp.text)
            return None
        data = resp.json()
        return data.get("access_token")


async def ensure_client_for_user(user: User) -> str | None:
    """
    For symmetry with other services, returns an access token string for the user
    or None if Google calendar is not available.
    """
    return await _get_google_access_token(user)


def _build_event_times(deadline: date | None) -> Tuple[dict, dict]:
    """
    Map an ActionItem.deadline date into Google Calendar start/end objects.
    If only a date is known, use an all‑day event.
    """
    if not deadline:
        # Default: today all‑day
        d = datetime.utcnow().date()
    else:
        d = deadline

    start = {"date": d.isoformat()}
    end = {"date": (d + timedelta(days=1)).isoformat()}
    return start, end


def _build_event_payload(user: User, action_item: ActionItem) -> dict:
    start, end = _build_event_times(action_item.deadline)
    summary = action_item.task[:100]
    description_lines = [
        f"Action item for {action_item.assignee_name or action_item.assignee_email or 'Unassigned'}",
    ]
    if action_item.mom and action_item.mom.meeting:
        meeting = action_item.mom.meeting
        description_lines.append(f"Meeting: {meeting.title or 'Untitled Meeting'}")
        description_lines.append(f"Meeting link: {meeting.meeting_url}")

    description = "\n".join(description_lines)

    return {
        "summary": summary,
        "description": description,
        "start": start,
        "end": end,
    }


async def create_event(user: User, action_item: ActionItem) -> tuple[str | None, str | None]:
    """
    Create a Google Calendar event for the given action item.

    Returns (event_id, html_link) or (None, None) if creation failed or calendar
    is not connected.
    """
    access_token = await _get_google_access_token(user)
    if not access_token:
        return None, None

    payload = _build_event_payload(user, action_item)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

        if resp.status_code not in (200, 201):
            log.error(
                "Failed to create Google Calendar event for action_item=%s: %s %s",
                action_item.id,
                resp.status_code,
                resp.text,
            )
            return None, None

        data = resp.json()
        return data.get("id"), data.get("htmlLink")


async def update_event(user: User, calendar_event: CalendarEvent, action_item: ActionItem) -> None:
    """Update an existing Google Calendar event when the action item changes."""
    if calendar_event.provider != CalendarProvider.google or not calendar_event.external_event_id:
        return

    access_token = await _get_google_access_token(user)
    if not access_token:
        return

    payload = _build_event_payload(user, action_item)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{calendar_event.external_event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

        if resp.status_code not in (200, 201):
            log.error(
                "Failed to update Google Calendar event id=%s: %s %s",
                calendar_event.external_event_id,
                resp.status_code,
                resp.text,
            )
            return


async def delete_event(user: User, calendar_event: CalendarEvent) -> None:
    """Delete a Google Calendar event when the action item is deleted."""
    if calendar_event.provider != CalendarProvider.google or not calendar_event.external_event_id:
        return

    access_token = await _get_google_access_token(user)
    if not access_token:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{calendar_event.external_event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if resp.status_code not in (200, 204):
            log.error(
                "Failed to delete Google Calendar event id=%s: %s %s",
                calendar_event.external_event_id,
                resp.status_code,
                resp.text,
            )
            return

