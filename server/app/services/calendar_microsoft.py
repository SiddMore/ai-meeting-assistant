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

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
MICROSOFT_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def _get_ms_access_token(user: User) -> str | None:
    """
    Exchange the stored Microsoft refresh token for a short‑lived access token.
    Returns None if the user is not connected or configuration is incomplete.
    """
    if not user.microsoft_refresh_token_enc:
        return None
    if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
        log.warning("Microsoft OAuth credentials not configured; skipping calendar sync")
        return None

    refresh_token = decrypt_token(user.microsoft_refresh_token_enc)
    tenant = settings.MICROSOFT_TENANT_ID or "common"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            MICROSOFT_TOKEN_URL.format(tenant=tenant),
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": " ".join(settings.MICROSOFT_GRAPH_SCOPES),
            },
        )
        if resp.status_code != 200:
            log.error("Failed to refresh Microsoft access token: %s %s", resp.status_code, resp.text)
            return None
        data = resp.json()
        return data.get("access_token")


async def ensure_client_for_user(user: User) -> str | None:
    """Return an access token string for the user or None if not available."""
    return await _get_ms_access_token(user)


def _build_event_times(deadline: date | None) -> Tuple[dict, dict]:
    if not deadline:
        d = datetime.utcnow().date()
    else:
        d = deadline

    # Represent as all‑day event in UTC
    start = {
        "dateTime": datetime(d.year, d.month, d.day, 9, 0).isoformat() + "Z",
        "timeZone": "UTC",
    }
    end = {
        "dateTime": datetime(d.year, d.month, d.day, 10, 0).isoformat() + "Z",
        "timeZone": "UTC",
    }
    return start, end


def _build_event_payload(user: User, action_item: ActionItem) -> dict:
    start, end = _build_event_times(action_item.deadline)
    subject = action_item.task[:100]
    body_lines = [
        f"Action item for {action_item.assignee_name or action_item.assignee_email or 'Unassigned'}",
    ]
    if action_item.mom and action_item.mom.meeting:
        meeting = action_item.mom.meeting
        body_lines.append(f"Meeting: {meeting.title or 'Untitled Meeting'}")
        body_lines.append(f"Meeting link: {meeting.meeting_url}")

    return {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": "\n".join(body_lines),
        },
        "start": start,
        "end": end,
    }


async def create_event(user: User, action_item: ActionItem) -> tuple[str | None, str | None]:
    """
    Create a Microsoft calendar event for the given action item.

    Returns (event_id, web_link) or (None, None) if creation failed or not connected.
    """
    access_token = await _get_ms_access_token(user)
    if not access_token:
        return None, None

    payload = _build_event_payload(user, action_item)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{MICROSOFT_GRAPH_BASE}/me/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

        if resp.status_code not in (200, 201):
            log.error(
                "Failed to create Microsoft event for action_item=%s: %s %s",
                action_item.id,
                resp.status_code,
                resp.text,
            )
            return None, None

        data = resp.json()
        return data.get("id"), data.get("webLink")


async def update_event(user: User, calendar_event: CalendarEvent, action_item: ActionItem) -> None:
    if calendar_event.provider != CalendarProvider.microsoft or not calendar_event.external_event_id:
        return

    access_token = await _get_ms_access_token(user)
    if not access_token:
        return

    payload = _build_event_payload(user, action_item)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{MICROSOFT_GRAPH_BASE}/me/events/{calendar_event.external_event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

        if resp.status_code not in (200, 202):
            log.error(
                "Failed to update Microsoft event id=%s: %s %s",
                calendar_event.external_event_id,
                resp.status_code,
                resp.text,
            )
            return


async def delete_event(user: User, calendar_event: CalendarEvent) -> None:
    if calendar_event.provider != CalendarProvider.microsoft or not calendar_event.external_event_id:
        return

    access_token = await _get_ms_access_token(user)
    if not access_token:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{MICROSOFT_GRAPH_BASE}/me/events/{calendar_event.external_event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if resp.status_code not in (200, 202, 204):
            log.error(
                "Failed to delete Microsoft event id=%s: %s %s",
                calendar_event.external_event_id,
                resp.status_code,
                resp.text,
            )
            return

