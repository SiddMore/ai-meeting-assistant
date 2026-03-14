import os
import sys
import asyncio
import uuid

# ensure the server/ directory is on sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

# set minimal environment variables before importing settings/app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_phase2.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_phase2.db")
os.environ.setdefault("SECRET_KEY", "testsecret")
# required but unused keys
os.environ.setdefault("GOOGLE_AI_API_KEY", "x")
os.environ.setdefault("DEEPL_API_KEY", "x")
os.environ.setdefault("REPLICATE_API_TOKEN", "x")
os.environ.setdefault("RECALL_AI_API_KEY", "x")
os.environ.setdefault("ENCRYPTION_KEY", "x")

from app.main import app  # noqa: E402
from app.db.session import init_db


def create_test_user(client: TestClient, email: str = "test@example.com", password: str = "password123") -> str:
    # register
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Test User", "password": password},
    )
    assert res.status_code == 201, res.text

    # login to obtain access token
    res = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert res.status_code == 200, res.text
    tokens = res.json()
    access = tokens["access_token"]
    return access


@pytest.fixture(scope="session")
def initialized_app():
    # ensure tables exist; create with a fresh event loop
    asyncio.run(init_db())
    yield app


@pytest.fixture

def client(initialized_app):
    with TestClient(initialized_app) as c:
        yield c


def test_meeting_lifecycle(client):
    import uuid
    email = f"lifecycle-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}

    # create a meeting record
    payload = {
        "title": "My Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
    }
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    meeting = res.json()
    # mock bot service sets meeting to bot_joining immediately
    assert meeting["status"] == "bot_joining"
    bot_id = meeting["recall_bot_id"]
    meeting_id = meeting["id"]

    # simulate bot events by posting directly to webhook
    def post_event(event: str, extra: dict = None):
        body = {"bot_id": bot_id, "event": event}
        if extra:
            body.update(extra)
        r = client.post("/api/v1/webhooks/recall", json=body)
        assert r.status_code == 200, r.text
        return r.json()

    post_event("bot.joining_call")
    r = client.get(f"/api/v1/meetings/{meeting_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "bot_joining"

    post_event("bot.in_call_recording")
    r = client.get(f"/api/v1/meetings/{meeting_id}", headers=headers)
    assert r.json()["status"] == "in_progress"

    # send a transcript chunk
    post_event("transcript.data", {"data": {"text": "Hello world", "speaker": "Alice", "language": "en", "start_time": 1, "is_final": True}})
    r = client.get(f"/api/v1/transcripts/{meeting_id}", headers=headers)
    chunks = r.json()
    assert len(chunks) == 1
    assert chunks[0]["text"] == "Hello world"

    # bot done
    post_event("bot.done")
    r = client.get(f"/api/v1/meetings/{meeting_id}", headers=headers)
    assert r.json()["status"] == "processing"


def test_invalid_meeting_url(client):
    """Creating a meeting with a malformed URL should be rejected early."""
    import uuid
    email = f"badurl-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}
    payload = {"title": "Bad URL", "platform": "google_meet", "meeting_url": "not-a-url"}
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    # Pydantic validation rejects non-URLs with 422 (validation error)
    assert res.status_code == 422


def test_selector_returns_recall():
    from app.services.bot_service import _select_bot_service, RecallBotService
    from app.core import config
    orig_provider = config.settings.BOT_PROVIDER
    orig_key = config.settings.RECALL_AI_API_KEY
    try:
        config.settings.BOT_PROVIDER = "recall"
        config.settings.RECALL_AI_API_KEY = "dummy"
        svc = _select_bot_service()
        assert isinstance(svc, RecallBotService)
    finally:
        config.settings.BOT_PROVIDER = orig_provider
        config.settings.RECALL_AI_API_KEY = orig_key


def test_recall_service_headers_and_401(monkeypatch):
    """Ensure RecallBotService uses the proper Authorization header and surfaces
    a 401 error when the API responds accordingly.
    """
    from app.services.bot_service import RecallBotService
    # ensure API key exists
    from app.core import config
    config.settings.RECALL_AI_API_KEY = "testkey"
    config.settings.RECALL_AI_REGION = "us-east-1"

    # Track calls to verify headers
    captured_headers = {}

    class DummyResp:
        def __init__(self, status, text, json_data=None):
            self.status_code = status
            self._text = text
            self._json = json_data or {}

        @property
        def text(self):
            return self._text

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"http error {self.status_code}")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            captured_headers["last"] = headers
            # simulate unauthorized if Authorization header is wrong
            if headers and headers.get("Authorization") != "Token testkey":
                return DummyResp(401, "unauthorized")
            return DummyResp(201, "{\"id\":\"bot123\"}", {"id": "bot123"})

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: DummyClient())

    recall = RecallBotService()
    # calling with valid url should succeed
    bot_id = asyncio.run(recall.deploy_bot("https://meet.google.com/abc", "https://example.com/webhook"))
    assert bot_id == "bot123"
    # Verify the Authorization header was in the captured request
    assert "Authorization" in captured_headers.get("last", {})
    assert "Token testkey" in captured_headers["last"]["Authorization"]

    # now simulate 401 by clearing key and trying to deploy
    config.settings.RECALL_AI_API_KEY = "wrong"
    recall_bad = RecallBotService()  # will use "wrong" key
    with pytest.raises(Exception) as excinfo:
        asyncio.run(recall_bad.deploy_bot("https://meet.google.com/abc", "https://example.com/webhook"))
    # Should get an error about 401
    assert "401" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__])
