"""
auth.py — Authentication routes.
Uses schemas from app.schemas.auth and security helpers from app.core.security.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import time
import uuid as _uuid

from app.db.session import get_db
from app.db.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
)
from app.core.redis import add_token_to_blocklist
from app.api.deps import get_current_user, get_token_from_request
from app.schemas.auth import UserCreate, UserOut

router = APIRouter()


# ── Request schemas ────────────────────────────────────────────────────────────

class SocialLoginRequest(BaseModel):
    email: EmailStr
    name: str
    provider: str  # 'google' | 'microsoft'
    provider_id: str
    avatar_url: Optional[str] = None


# ── Cookie helpers ─────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Write HTTP-only auth cookies. secure=False for local HTTP dev."""
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,   # Set to True in production (HTTPS only)
        samesite="lax",
        max_age=60 * 15,  # 15 minutes
    )
    response.set_cookie(
        key="refresh_token",
        value=f"Bearer {refresh_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )


# ── Register ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user account with email + password."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Standard OAuth2 password flow for NextAuth CredentialsProvider.
    `form_data.username` is the user's email.
    Returns tokens in the response body (for NextAuth) and sets HTTP-only cookies.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ── Social (OAuth) Login ───────────────────────────────────────────────────────

@router.post("/social")
async def social_login(
    payload: SocialLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by NextAuth.js server-side after a successful OAuth callback.
    Creates or links the user and returns JWTs.
    """
    if payload.provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider",
        )

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=payload.email,
            name=payload.name,
            avatar_url=payload.avatar_url,
            is_active=True,
            is_verified=True,  # OAuth users are pre-verified by their provider
        )
        if payload.provider == "google":
            user.google_id = payload.provider_id
        else:
            user.microsoft_id = payload.provider_id
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Link provider ID if not already set
        updated = False
        if payload.provider == "google" and not user.google_id:
            user.google_id = payload.provider_id
            updated = True
        elif payload.provider == "microsoft" and not user.microsoft_id:
            user.microsoft_id = payload.provider_id
            updated = True
        if updated:
            await db.commit()
            await db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ── Refresh Token ──────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token_endpoint(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Use a refresh token (from cookie or header) to issue a new access token."""
    token = None
    cookie_val = request.cookies.get("refresh_token")
    if cookie_val:
        token = cookie_val.split(" ", 1)[1] if cookie_val.startswith("Bearer ") else cookie_val

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    payload = await verify_token(token, token_type="refresh")
    user_id_str = payload.get("sub")

    try:
        user_id = _uuid.UUID(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(subject=str(user.id))
    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 15,
    )
    return {"access_token": new_access_token, "token_type": "bearer"}


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    response: Response,
    token: str = Depends(get_token_from_request),
):
    """Revoke the current access token and clear auth cookies."""
    try:
        payload = await verify_token(token, token_type="access")
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            expires_in = int(exp - time.time())
            if expires_in > 0:
                await add_token_to_blocklist(jti, expires_in)
    except Exception:
        pass  # If token is already invalid, just clear cookies

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "success", "detail": "Logged out successfully"}


# ── Me ─────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
