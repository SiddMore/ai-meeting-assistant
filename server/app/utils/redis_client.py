"""
redis_client.py — Centralized Redis connection manager.
"""
import redis.asyncio as redis
from contextlib import asynccontextmanager
from app.core.config import settings
import logging

log = logging.getLogger(__name__)

@asynccontextmanager
async def get_redis():
    """
    Async context manager for Redis connections.
    Uses the password-protected URL from settings.
    """
    client = redis.from_url(
        settings.REDIS_URL, 
        decode_responses=True,
        encoding="utf-8"
    )
    try:
        yield client
    except Exception as e:
        log.error(f"Redis connection error: {e}")
        raise e
    finally:
        await client.close()