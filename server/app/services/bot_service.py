import asyncio
import logging
import uuid
from typing import Protocol, Optional
from app.core.config import settings

log = logging.getLogger(__name__)

class BotService(Protocol):
    """Interface that all bot service implementations must satisfy."""
    async def deploy_bot(
        self,
        meeting_url: str,
        webhook_url: str,
        bot_name: str = "AI Meeting Assistant",
    ) -> str:
        ...

    async def stop_bot(self, bot_id: str) -> None:
        ...

    async def get_bot_status(self, bot_id: str) -> dict:
        ...

class MockBotService:
    """Simulates the bot lifecycle locally for development/testing."""
    async def deploy_bot(
        self,
        meeting_url: str,
        webhook_url: str,
        bot_name: str = "AI Meeting Assistant",
    ) -> str:
        bot_id = f"mock-bot-{uuid.uuid4().hex[:12]}"
        log.info(f"MOCK BOT: Deployment requested. ID: {bot_id}")
        return bot_id

    async def stop_bot(self, bot_id: str) -> None:
        pass

    async def get_bot_status(self, bot_id: str) -> dict:
        return {"bot_id": bot_id, "status": "mock", "provider": "mock"}

class RecallBotService:
    """Real implementation for Recall.ai API."""
    def __init__(self):
        self.api_key = settings.RECALL_AI_API_KEY or ""
        self.base_url = getattr(settings, "RECALL_AI_REGION", "us-east-1") + ".recall.ai"

    async def deploy_bot(
        self,
        meeting_url: str,
        webhook_url: str,
        bot_name: str = "AI Meeting Assistant",
    ) -> str:
        if not self.api_key:
            raise ValueError("Cannot deploy: RECALL_AI_API_KEY is missing.")

        import httpx
        payload = {"meeting_url": meeting_url, "bot_name": bot_name}
        if webhook_url:
            payload["webhook_url"] = webhook_url

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://{self.base_url}/api/v1/bot"
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                raise Exception("Recall.ai returned 401 Unauthorized - check API key")
            resp.raise_for_status()
            data = resp.json()
            return data.get("id") or data.get("bot_id")

    async def stop_bot(self, bot_id: str) -> None:
        import httpx
        headers = {"Authorization": f"Token {self.api_key}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"https://{self.base_url}/api/v1/bot/{bot_id}"
                await client.delete(url, headers=headers)
            except Exception:
                pass

    async def get_bot_status(self, bot_id: str) -> dict:
        import httpx
        headers = {"Authorization": f"Token {self.api_key}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://{self.base_url}/api/v1/bot/{bot_id}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

# --- HELPER FUNCTIONS ---

async def _validate_meeting_url(url: str) -> bool:
    """Validates if the URL is a proper web link."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def _select_bot_service() -> BotService:
    provider = (settings.BOT_PROVIDER or "mock").lower().strip()
    if provider == "recall":
        if not settings.RECALL_AI_API_KEY:
            print("⚠️ WARNING: BOT_PROVIDER is 'recall' but API Key is missing. Using MOCK mode.")
            return MockBotService()
        return RecallBotService()
    return MockBotService()

# Singleton instance
bot_service = _select_bot_service()