"""
Tests for Socket.IO server with Redis buffer service integration.
"""

import pytest
import socketio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import os
os.environ["TESTING"] = "true"

from app.realtime.socketio_server import (
    create_sio_server, _meeting_room, redis_buffer_service,
    bot_transcript_chunk, catch_me_up, bot_done, bot_fatal_error
)
from app.services.redis_buffer_service import RedisBufferService
from app.core.test_config import settings

# Override settings for testing
from app.core.config import Settings
Settings._pydantic_core._config.extra = "allow"


@pytest.fixture
def mock_sio():
    """Create a mock Socket.IO server instance."""
    sio = create_sio_server()
    return sio


@pytest.fixture
def mock_redis_buffer():
    """Create a mock Redis buffer service."""
    return AsyncMock(spec=RedisBufferService)


@pytest.fixture
def mock_sid():
    """Create a mock Socket.IO session ID."""
    return "mock_sid_123"


@pytest.fixture
def mock_meeting_id():
    """Create a mock meeting ID."""
    return "meeting_456"


@pytest.fixture
def mock_transcript_chunk():
    """Create a mock transcript chunk."""
    return {
        "chunk_id": "chunk_789",
        "speaker": "John",
        "text": "This is a test transcript.",
        "language": "en",
        "start_time": datetime.now(timezone.utc),
        "is_final": True
    }


@pytest.fixture
def mock_bot_token():
    """Create a mock bot token."""
    return "bot_token_789"


@pytest.fixture
def mock_auth():
    """Create mock authentication data."""
    return {
        "token": "access_token_123",
        "bot_token": "bot_token_789"
    }


@pytest.fixture
def mock_data():
    """Create mock data payload."""
    return {
        "meeting_id": "meeting_456",
        "bot_token": "bot_token_789",
        "data": {
            "chunk": {
                "chunk_id": "chunk_789",
                "speaker": "John",
                "text": "This is a test transcript.",
                "language": "en",
                "start_time": datetime.now(timezone.utc),
                "is_final": True
            }
        }
    }


@pytest.fixture
def mock_bot_event_data():
    """Create mock bot event data."""
    return {
        "bot_token": "bot_token_789",
        "meeting_id": "meeting_456",
        "data": {
            "chunk": {
                "chunk_id": "chunk_789",
                "speaker": "John",
                "text": "This is a test transcript.",
                "language": "en",
                "start_time": datetime.now(timezone.utc),
                "is_final": True
            }
        }
    }


class TestSocketIOServerRedisIntegration:
    """Tests for Socket.IO server with Redis buffer integration."""

    def test_meeting_room_format(self, mock_meeting_id):
        """Test meeting room format."""
        room = _meeting_room(mock_meeting_id)
        assert room == f"meeting:{mock_meeting_id}"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_transcript_chunk_success(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token, mock_transcript_chunk
    ):
        """Test successful bot transcript chunk handling."""
        # Setup mock data
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": mock_meeting_id,
            "data": {
                "chunk": mock_transcript_chunk
            }
        }

        # Mock Redis buffer service
        mock_buffer_service.add_chunk_to_buffer.return_value = True
        mock_buffer_service.get_buffer_status.return_value = {
            "total_chunks": 1,
            "meeting_id": mock_meeting_id
        }

        # Mock bot token verification
        with patch("app.realtime.socketio_server._verify_bot_token", return_value=mock_meeting_id):
            result = await bot_transcript_chunk(mock_sid, data)

        assert result["ok"] is True
        mock_buffer_service.add_chunk_to_buffer.assert_called_once_with(
            meeting_id=mock_meeting_id,
            chunk=mock_transcript_chunk
        )

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_transcript_chunk_missing_token(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id
    ):
        """Test bot transcript chunk with missing token."""
        data = {
            "meeting_id": mock_meeting_id,
            "data": {}
        }

        result = await bot_transcript_chunk(mock_sid, data)
        assert result["ok"] is False
        assert result["error"] == "missing bot_token"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_transcript_chunk_invalid_token(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test bot transcript chunk with invalid token."""
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": mock_meeting_id,
            "data": {}
        }

        with patch("app.realtime.socketio_server._verify_bot_token", return_value=None):
            result = await bot_transcript_chunk(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "invalid bot_token"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_transcript_chunk_mismatch(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test bot transcript chunk with token/ meeting ID mismatch."""
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": "different_meeting",
            "data": {}
        }

        with patch("app.realtime.socketio_server._verify_bot_token", return_value=mock_meeting_id):
            result = await bot_transcript_chunk(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "bot_token_meeting_mismatch"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_transcript_chunk_meeting_not_found(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test bot transcript chunk when meeting is not found."""
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": mock_meeting_id,
            "data": {}
        }

        with patch("app.realtime.socketio_server._verify_bot_token", return_value=mock_meeting_id):
            with patch("app.realtime.socketio_server.uuid.UUID"):
                with patch("app.realtime.socketio_server.select"):
                    with patch("app.realtime.socketio_server.AsyncSessionLocal"):
                        result = await bot_transcript_chunk(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "meeting_not_found"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_catch_me_up_success(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id
    ):
        """Test successful catch_me_up event."""
        data = {"meeting_id": mock_meeting_id}

        # Mock Redis buffer service
        mock_buffer_service.get_buffered_chunks.return_value = [
            {
                "chunk_id": "chunk_789",
                "speaker": "John",
                "text": "This is a test transcript.",
                "language": "en",
                "start_time": datetime.now(timezone.utc),
                "is_final": True
            }
        ]

        result = await catch_me_up(mock_sid, data)

        assert result["ok"] is True
        mock_buffer_service.get_buffered_chunks.assert_called_once_with(mock_meeting_id)

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_catch_me_up_missing_meeting_id(
        self, mock_buffer_service, mock_sio, mock_sid
    ):
        """Test catch_me_up with missing meeting ID."""
        data = {}

        result = await catch_me_up(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "meeting_id is required"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_done_success(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test successful bot_done event."""
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": mock_meeting_id
        }

        # Mock bot token verification
        with patch("app.realtime.socketio_server._verify_bot_token", return_value=mock_meeting_id):
            result = await bot_done(mock_sid, data)

        assert result["ok"] is True
        mock_buffer_service.clear_buffer.assert_called_once_with(mock_meeting_id)

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_done_missing_token(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id
    ):
        """Test bot_done with missing token."""
        data = {"meeting_id": mock_meeting_id}

        result = await bot_done(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "missing bot_token"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_fatal_error_success(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test successful bot_fatal_error event."""
        data = {
            "bot_token": mock_bot_token,
            "meeting_id": mock_meeting_id
        }

        # Mock bot token verification
        with patch("app.realtime.socketio_server._verify_bot_token", return_value=mock_meeting_id):
            result = await bot_fatal_error(mock_sid, data)

        assert result["ok"] is True
        mock_buffer_service.clear_buffer.assert_called_once_with(mock_meeting_id)

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_bot_fatal_error_missing_token(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id
    ):
        """Test bot_fatal_error with missing token."""
        data = {"meeting_id": mock_meeting_id}

        result = await bot_fatal_error(mock_sid, data)

        assert result["ok"] is False
        assert result["error"] == "missing bot_token"

    @patch("app.realtime.socketio_server.redis_buffer_service", new_callable=AsyncMock)
    async def test_error_handling(
        self, mock_buffer_service, mock_sio, mock_sid, mock_meeting_id, mock_bot_token
    ):
        """Test error handling in socket events."""
        # Test client_ping error handling
        with patch("app.realtime.socketio_server.client_ping") as mock_client_ping:
            mock_client_ping.side_effect = Exception("Test error")
            result = await mock_sio.call_event("client_ping", None)
            assert result["ok"] is False
            assert result["error"] == "client_ping_failed"

        # Test join_meeting error handling
        with patch("app.realtime.socketio_server.join_meeting") as mock_join_meeting:
            mock_join_meeting.side_effect = Exception("Test error")
            result = await mock_sio.call_event("join_meeting", {"meeting_id": mock_meeting_id})
            assert result["ok"] is False
            assert result["error"] == "join_meeting_failed"

        # Test bot_transcript_chunk error handling
        with patch("app.realtime.socketio_server.bot_transcript_chunk") as mock_bot_transcript:
            mock_bot_transcript.side_effect = Exception("Test error")
            data = {
                "bot_token": mock_bot_token,
                "meeting_id": mock_meeting_id,
                "data": {}
            }
            result = await mock_sio.call_event("bot_transcript_chunk", data)
            assert result["ok"] is False
            assert result["error"] == "bot_transcript_chunk_failed"

        # Test bot_done error handling
        with patch("app.realtime.socketio_server.bot_done") as mock_bot_done:
            mock_bot_done.side_effect = Exception("Test error")
            data = {
                "bot_token": mock_bot_token,
                "meeting_id": mock_meeting_id
            }
            result = await mock_sio.call_event("bot_done", data)
            assert result["ok"] is False
            assert result["error"] == "bot_done_failed"

        # Test bot_fatal_error error handling
        with patch("app.realtime.socketio_server.bot_fatal_error") as mock_bot_fatal:
            mock_bot_fatal.side_effect = Exception("Test error")
            data = {
                "bot_token": mock_bot_token,
                "meeting_id": mock_meeting_id
            }
            result = await mock_sio.call_event("bot_fatal_error", data)
            assert result["ok"] is False
            assert result["error"] == "bot_fatal_error_failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])