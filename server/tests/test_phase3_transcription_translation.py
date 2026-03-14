import os
import sys
import asyncio
import uuid
import base64
import io

# ensure the server/ directory is on sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

# set minimal environment variables before importing settings/app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_phase3.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test_phase3.db")
os.environ.setdefault("SECRET_KEY", "testsecret")
# required but unused keys
os.environ.setdefault("GOOGLE_AI_API_KEY", "x")
os.environ.setdefault("DEEPL_API_KEY", "x")
os.environ.setdefault("REPLICATE_API_TOKEN", "x")
os.environ.setdefault("RECALL_AI_API_KEY", "x")
os.environ.setdefault("ENCRYPTION_KEY", "x")
# Set mock API keys for testing
os.environ.setdefault("OPENAI_API_KEY", "sk-test123")
os.environ.setdefault("DEEPL_API_KEY", "deepl-test123")

from app.main import app  # noqa: E402
from app.db.session import init_db
from app.workers.transcription import _transcribe_audio_chunk, _save_transcript_chunk
from app.workers.translation import _translate_meeting_transcript


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


def test_transcription_with_mock_data(client):
    """Test transcription processing with mock audio data."""
    email = f"transcription-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}

    # Create a meeting
    payload = {
        "title": "Transcription Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/test-123",
    }
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    meeting = res.json()
    meeting_id = meeting["id"]

    # Create mock audio data (base64 encoded WAV)
    # This is a minimal WAV header + silence
    mock_wav = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00"
    audio_base64 = base64.b64encode(mock_wav).decode()

    # Process audio chunk via Celery task (mock)
    chunk_data = {
        "meeting_id": meeting_id,
        "bot_id": "test-bot",
        "audio_base64": audio_base64,
        "start_time": 0.0,
        "end_time": 1.0,
        "language": "en",
    }

    # Since we're using mock transcription, it should work without real APIs
    result = asyncio.run(_transcribe_audio_chunk(chunk_data))
    assert "text" in result
    assert result["language"] == "en"
    assert result["is_final"] is True


def test_translation_task(client):
    """Test translation task processing."""
    email = f"translation-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}

    # Create a meeting
    payload = {
        "title": "Translation Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/test-456",
    }
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    meeting = res.json()
    meeting_id = meeting["id"]

    # Add some transcript chunks first
    def post_event(event: str, extra: dict = None):
        body = {"bot_id": meeting["recall_bot_id"], "event": event}
        if extra:
            body.update(extra)
        r = client.post("/api/v1/webhooks/recall", json=body)
        assert r.status_code == 200, r.text
        return r.json()

    # Send transcript chunks
    post_event("transcript.data", {"data": {"text": "Hello world", "speaker": "Alice", "language": "en", "start_time": 1, "is_final": True}})
    post_event("transcript.data", {"data": {"text": "How are you?", "speaker": "Bob", "language": "en", "start_time": 2, "is_final": True}})

    # End meeting to trigger finalization
    post_event("bot.done")

    # Run translation task (mock)
    result = asyncio.run(_translate_meeting_transcript(meeting_id, "en"))
    # Since it's async and doesn't return anything, just check that it completed without error

    # Check that transcript was updated
    res = client.get(f"/api/v1/meetings/{meeting_id}", headers=headers)
    assert res.status_code == 200
    meeting_data = res.json()
    assert meeting_data["transcript"] is not None
    assert meeting_data["transcript"]["content_raw"] is not None


def test_meeting_with_transcript_response(client):
    """Test that meeting responses include transcript data."""
    email = f"transcript-response-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}

    # Create a meeting
    payload = {
        "title": "Response Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/test-789",
    }
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    meeting = res.json()

    # Initially no transcript
    assert meeting.get("transcript") is None

    # Get meeting should include transcript field (even if null)
    res = client.get(f"/api/v1/meetings/{meeting['id']}", headers=headers)
    assert res.status_code == 200
    meeting_data = res.json()
    assert "transcript" in meeting_data


def test_transcript_chunks_endpoint(client):
    """Test retrieving transcript chunks."""
    email = f"chunks-{uuid.uuid4()}@example.com"
    access = create_test_user(client, email=email)
    headers = {"Authorization": f"Bearer {access}"}

    # Create a meeting
    payload = {
        "title": "Chunks Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/test-chunks",
    }
    res = client.post("/api/v1/meetings", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    meeting = res.json()
    meeting_id = meeting["id"]

    # Initially no chunks
    res = client.get(f"/api/v1/transcripts/{meeting_id}", headers=headers)
    assert res.status_code == 200
    chunks = res.json()
    assert len(chunks) == 0

    # Add chunks via webhook
    def post_event(event: str, extra: dict = None):
        body = {"bot_id": meeting["recall_bot_id"], "event": event}
        if extra:
            body.update(extra)
        r = client.post("/api/v1/webhooks/recall", json=body)
        assert r.status_code == 200, r.text
        return r.json()

    post_event("transcript.data", {"data": {"text": "First chunk", "speaker": "Alice", "language": "en", "start_time": 0, "is_final": True}})
    post_event("transcript.data", {"data": {"text": "Second chunk", "speaker": "Bob", "language": "en", "start_time": 1, "is_final": True}})

    # Check chunks are returned
    res = client.get(f"/api/v1/transcripts/{meeting_id}", headers=headers)
    assert res.status_code == 200
    chunks = res.json()
    assert len(chunks) == 2
    assert chunks[0]["text"] == "First chunk"
    assert chunks[1]["text"] == "Second chunk"
    assert chunks[0]["speaker"] == "Alice"
    assert chunks[1]["speaker"] == "Bob"