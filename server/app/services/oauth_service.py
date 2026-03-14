"""
oauth_service.py — Google and Microsoft OAuth2 exchange helpers.
"""
from __future__ import annotations

import httpx

from app.core.config import settings


# ── Google ─────────────────────────────────────────────────────────────────────
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def get_google_auth_url(state: str) -> str:
    """Build the Google OAuth2 redirect URL."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_CALENDAR_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_google_code(code: str) -> dict:
    """Exchange an authorization code for Google tokens + user profile."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    return {
        "provider_id": userinfo["sub"],
        "email": userinfo["email"],
        "name": userinfo.get("name", ""),
        "avatar_url": userinfo.get("picture"),
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
    }


# ── Microsoft ──────────────────────────────────────────────────────────────────
MICROSOFT_AUTH_BASE = "https://login.microsoftonline.com"
MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"


def get_microsoft_auth_url(state: str) -> str:
    """Build the Microsoft OAuth2 redirect URL."""
    tenant = settings.MICROSOFT_TENANT_ID
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.MICROSOFT_GRAPH_SCOPES),
        "state": state,
        "response_mode": "query",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/authorize?{query}"


async def exchange_microsoft_code(code: str) -> dict:
    """Exchange an authorization code for Microsoft tokens + user profile."""
    tenant = settings.MICROSOFT_TENANT_ID
    token_url = f"{MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/token"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            token_url,
            data={
                "code": code,
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        me_resp = await client.get(
            MICROSOFT_GRAPH_ME_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        me_resp.raise_for_status()
        me = me_resp.json()

    return {
        "provider_id": me["id"],
        "email": me.get("mail") or me.get("userPrincipalName", ""),
        "name": me.get("displayName", ""),
        "avatar_url": None,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
    }
