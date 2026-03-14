"""
Test suite for Socket.IO server integration.
"""

import pytest
import socketio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import uuid

from app.realtime.socketio_server import (
    create_sio_server, _meeting_room, redis_buffer_service,
    bot_transcript_chunk, catch_me_up, bot_done, bot_fatal_error
)
from app.services.redis_buffer_service import RedisBufferService
from app.core.test_config import settings

# Override settings for testing
from app.core.config import Settings
Settings._pydantic_core._config.extra = "allow"


class TestSocketIOIntegration:
    """Test suite for Socket.IO server integration."""

    @pytest.fixture
    def mock_sio(self):
        """Create a mock Socket.IO server instance."""
        sio = create_sio_server()
        return sio

    @pytest.fixture
    def mock_redis_buffer(self):
        """Create a mock Redis buffer service."""
        return AsyncMock(spec=RedisBufferService)

    @pytest.fixture
    def mock_sid(self):
        """Create a mock Socket.IO session ID."""
        return "mock_sid_123"

    @pytest.fixture
    def mock_meeting_id(self):
        """Create a mock meeting ID."""
        return "meeting_456"

    @pytest.fixture
    def sample_transcript_chunk(self):
        """Create a sample transcript chunk."""
        return {
            "timestamp": 1,
            "text": "Hello everyone",
            "speaker": "Test Speaker",
            "confidence": 0.95
        }

    @pytest.fixture
    def sample_error_message(self):
        """Create a sample error message."""
        return "Connection lost with the bot"

    async def test_meeting_room_creation(self, mock_meeting_id):
        """Test meeting room creation."""
        room = _meeting_room(mock_meeting_id)
        assert room == f"meeting:{mock_meeting_id}"

    async def test_bot_transcript_chunk_basic(self, mock_sio, mock_redis_buffer, mock_sid,
                                            mock_meeting_id, sample_transcript_chunk):
        """Test basic bot transcript chunk functionality."""
        # Mock Redis buffer service
        mock_redis_buffer.add_chunk.return_value = True

        # Call the function
        await bot_transcript_chunk(mock_sio, mock_sid, mock_meeting_id, sample_transcript_chunk)

        # Assertions
        mock_redis_buffer.add_chunk.assert_called_once_with(
            mock_meeting_id, sample_transcript_chunk
        )
        mock_sio.emit.assert_called_once_with(
            "transcript_chunk",
            sample_transcript_chunk,
            room=_meeting_room(mock_meeting_id)
        )

    async def test_bot_transcript_chunk_redis_failure(self, mock_sio, mock_redis_buffer, mock_sid,
                                                    mock_meeting_id, sample_transcript_chunk):
        """Test bot transcript chunk when Redis fails."""
        # Mock Redis buffer service to raise an exception
        mock_redis_buffer.add_chunk.side_effect = Exception("Redis connection error")

        # Call the function
        with pytest.raises(Exception):
            await bot_transcript_chunk(mock_sio, mock_sid, mock_meeting_id, sample_transcript_chunk)

        # Assertions
        mock_redis_buffer.add_chunk.assert_called_once_with(
            mock_meeting_id, sample_transcript_chunk
        )
        mock_sio.emit.assert_not_called()

    async def test_catch_me_up_basic(self, mock_sio, mock_redis_buffer, mock_sid,
                                   mock_meeting_id, sample_transcript_chunk):
        """Test basic catch-me-up functionality."""
        # Mock Redis buffer service
        mock_redis_buffer.get_recent_chunks.return_value = [
            sample_transcript_chunk
        ]
        mock_redis_buffer.get_buffer_size.return_value = 1

        # Call the function
        await catch_me_up(mock_sio, mock_sid, mock_meeting_id)

        # Assertions
        mock_redis_buffer.get_recent_chunks.assert_called_once_with(mock_meeting_id, 100)
        mock_redis_buffer.get_buffer_size.assert_called_once_with(mock_meeting_id)
        mock_sio.emit.assert_called_once_with(
            "catch_up",
            {
                "meeting_id": mock_meeting_id,
                "chunks": [sample_transcript_chunk],
                "total_chunks": 1,
                "buffer_size": 1,
                "timestamp": mock.ANY
            },
            room=_meeting_room(mock_meeting_id)
        )

    async def test_catch_me_up_with_custom_count(self, mock_sio, mock_redis_buffer, mock_sid,
                                               mock_meeting_id, sample_transcript_chunk):
        """Test catch-me-up with custom chunk count."""
        chunk_count = 50
        # Mock Redis buffer service
        mock_redis_buffer.get_recent_chunks.return_value = [
            sample_transcript_chunk
        ]
        mock_redis_buffer.get_buffer_size.return_value = 1

        # Call the function
        await catch_me_up(mock_sio, mock_sid, mock_meeting_id, chunk_count)

        # Assertions
        mock_redis_buffer.get_recent_chunks.assert_called_once_with(mock_meeting_id, chunk_count)

    async def test_bot_done_basic(self, mock_sio, mock_sid, mock_meeting_id):
        """Test basic bot done functionality."""
        # Call the function
        await bot_done(mock_sio, mock_sid, mock_meeting_id)

        # Assertions
        mock_sio.emit.assert_called_once_with(
            "bot_done",
            {"meeting_id": mock_meeting_id},
            room=_meeting_room(mock_meeting_id)
        )

    async def test_bot_fatal_error_basic(self, mock_sio, mock_sid, mock_meeting_id, sample_error_message):
        """Test basic bot fatal error functionality."""
        # Call the function
        await bot_fatal_error(mock_sio, mock_sid, mock_meeting_id, sample_error_message)

        # Assertions
        mock_sio.emit.assert_called_once_with(
            "bot_error",
            {"meeting_id": mock_meeting_id, "error": sample_error_message},
            room=_meeting_room(mock_meeting_id)
        )

    async def test_socketio_server_creation(self):
        """Test Socket.IO server creation."""
        sio = create_sio_server()
        assert sio is not None
        assert sio.async_mode == "asgi"

    async def test_socketio_server_configuration(self):
        """Test Socket.IO server configuration."""
        sio = create_sio_server()
        assert sio.cors_allowed_origins == settings.ALLOWED_ORIGINS
        assert sio.ping_interval == 10
        assert sio.ping_timeout == 20
        assert sio.max_http_buffer_size == 10 * 1024 * 1024

    async def test_meeting_room_formatting(self):
        """Test meeting room formatting."""
        meeting_id = "test-meeting-123"
        room = _meeting_room(meeting_id)
        assert room == f"meeting:{meeting_id}"

    async def test_socketio_event_handlers_registration(self, mock_sio):
        """Test that Socket.IO event handlers are properly registered."""
        # This test ensures that the event handlers are attached to the Socket.IO server
        # We'll check for the presence of key event handlers
        event_names = [event.name for event in mock_sio.event_handlers]
        
        assert "transcript_chunk" in event_names
        assert "catch_up" in event_names
        assert "bot_done" in event_names
        assert "bot_error" in event_names

    async def test_socketio_connection_event(self, mock_sio):
        """Test Socket.IO connection event."""
        # Mock the connection event handler
        @mock_sio.event
        async def connect(sid, environ):
            pass

        # Simulate a connection
        await mock_sio.connect("test_sid")
        
        # Verify connection handling
        assert "test_sid" in mock_sio.sids

    async def test_socketio_disconnection_event(self, mock_sio):
        """Test Socket.IO disconnection event."""
        # Mock the disconnection event handler
        @mock_sio.event
        async def disconnect(sid):
            pass

        # Simulate a disconnection
        await mock_sio.disconnect("test_sid")
        
        # Verify disconnection handling
        assert "test_sid" not in mock_sio.sids

    async def test_socketio_room_joining(self, mock_sio, mock_sid, mock_meeting_id):
        """Test joining a meeting room."""
        room = _meeting_room(mock_meeting_id)
        
        # Simulate joining a room
        await mock_sio.enter_room(mock_sid, room)
        
        # Verify room membership
        assert room in mock_sio.rooms(mock_sid)

    async def test_socketio_room_leaving(self, mock_sio, mock_sid, mock_meeting_id):
        """Test leaving a meeting room."""
        room = _meeting_room(mock_meeting_id)
        
        # First join the room
        await mock_sio.enter_room(mock_sid, room)
        
        # Then leave the room
        await mock_sio.leave_room(mock_sid, room)
        
        # Verify room membership
        assert room not in mock_sio.rooms(mock_sid)

    async def test_socketio_emit_to_room(self, mock_sio, mock_meeting_id):
        """Test emitting to a room."""
        room = _meeting_room(mock_meeting_id)
        message = {"test": "data"}
        
        # Mock the emit function
        mock_sio.emit = AsyncMock()
        
        # Emit to the room
        await mock_sio.emit("test_event", message, room=room)
        
        # Verify emit was called
        mock_sio.emit.assert_called_once_with("test_event", message, room=room)

    async def test_socketio_emit_to_sid(self, mock_sio, mock_sid):
        """Test emitting to a specific session ID."""
        message = {"test": "data"}
        
        # Mock the emit function
        mock_sio.emit = AsyncMock()
        
        # Emit to the session ID
        await mock_sio.emit("test_event", message, to=mock_sid)
        
        # Verify emit was called
        mock_sio.emit.assert_called_once_with("test_event", message, to=mock_sid)

    async def test_socketio_multiple_clients(self, mock_sio):
        """Test handling multiple Socket.IO clients."""
        # Simulate multiple clients connecting
        sids = [f"client_{i}" for i in range(5)]
        
        for sid in sids:
            await mock_sio.connect(sid)
        
        # Verify all clients are connected
        assert len(mock_sio.sids) == 5
        
        # Disconnect all clients
        for sid in sids:
            await mock_sio.disconnect(sid)
        
        # Verify all clients are disconnected
        assert len(mock_sio.sids) == 0

    async def test_socketio_error_handling(self, mock_sio):
        """Test Socket.IO error handling."""
        # Mock an error handler
        @mock_sio.event
        async def error(sid, error):
            pass
        
        # Simulate an error
        with pytest.raises(Exception):
            await mock_sio.handle_error("test_sid", Exception("Test error"))

    async def test_socketio_custom_event(self, mock_sio, mock_sid):
        """Test custom Socket.IO event handling."""
        # Define a custom event
        @mock_sio.event
        async def custom_event(sid, data):
            return {"status": "received", "data": data}
        
        # Simulate the custom event
        result = await mock_sio.call_event("custom_event", "test_data", mock_sid)
        
        # Verify the result
        assert result == {"status": "received", "data": "test_data"}

    async def test_socketio_namespace_handling(self, mock_sio):
        """Test Socket.IO namespace handling."""
        # Create a namespace
        namespace = "/test"
        
        # Define a namespace event
        @mock_sio.event(namespace=namespace)
        async def namespace_event(sid, data):
            return {"namespace": namespace, "data": data}
        
        # Simulate the namespace event
        result = await mock_sio.call_event("namespace_event", "test_data", namespace=namespace)
        
        # Verify the result
        assert result == {"namespace": namespace, "data": "test_data"}

    async def test_socketio_room_broadcast(self, mock_sio, mock_meeting_id):
        """Test broadcasting to a room."""
        room = _meeting_room(mock_meeting_id)
        message = {"broadcast": "test"}
        
        # Mock the emit function
        mock_sio.emit = AsyncMock()
        
        # Broadcast to the room
        await mock_sio.emit("broadcast_event", message, room=room, skip_sid="excluded_sid")
        
        # Verify emit was called
        mock_sio.emit.assert_called_once_with("broadcast_event", message, room=room, skip_sid="excluded_sid")

    async def test_socketio_room_multiple_broadcasts(self, mock_sio, mock_meeting_id):
        """Test multiple broadcasts to a room."""
        room = _meeting_room(mock_meeting_id)
        messages = [{"id": i, "data": f"test_{i}"} for i in range(3)]
        
        # Mock the emit function
        mock_sio.emit = AsyncMock()
        
        # Broadcast multiple messages
        for message in messages:
            await mock_sio.emit("multiple_event", message, room=room)
        
        # Verify emit was called multiple times
        assert mock_sio.emit.call_count == 3

    async def test_socketio_room_with_multiple_sids(self, mock_sio, mock_meeting_id):
        """Test room with multiple session IDs."""
        room = _meeting_room(mock_meeting_id)
        sids = [f"sid_{i}" for i in range(3)]
        
        # Add sids to the room
        for sid in sids:
            await mock_sio.enter_room(sid, room)
        
        # Verify all sids are in the room
        for sid in sids:
            assert room in mock_sio.rooms(sid)
        
        # Get all sids in the room
        room_sids = mock_sio.rooms(room)
        assert len(room_sids) == 3

    async def test_socketio_room_removal(self, mock_sio, mock_meeting_id):
        """Test room removal when last client disconnects."""
        room = _meeting_room(mock_meeting_id)
        sid = "test_sid"
        
        # Add sid to the room
        await mock_sio.enter_room(sid, room)
        
        # Verify room exists
        assert room in mock_sio.rooms(sid)
        
        # Disconnect the client
        await mock_sio.disconnect(sid)
        
        # Verify room is removed
        assert room not in mock_sio.rooms(sid)
        assert room not in mock_sio.rooms