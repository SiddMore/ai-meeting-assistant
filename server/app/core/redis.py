import redis.asyncio as redis
from app.core.config import settings

redis_client = None

async def init_redis():
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

async def get_redis() -> redis.Redis:
    if redis_client is None:
        await init_redis()
    return redis_client

async def add_token_to_blocklist(jti: str, expires_in: int):
    try:
        client = await get_redis()
        await client.setex(f"blocklist:{jti}", expires_in, "true")
    except Exception:
        pass  # Redis unavailable, gracefully degrade

async def is_token_blocklisted(jti: str) -> bool:
    try:
        client = await get_redis()
        result = await client.get(f"blocklist:{jti}")
        return result == "true"
    except Exception:
        return False  # Redis unavailable, gracefully degrade
