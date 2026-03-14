"""
Test suite for RedisBufferService.

Tests cover all core functionality including chunk addition, retrieval, buffer management,
and error handling scenarios.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.redis_buffer_service import RedisBufferService
from app.utils.redis_client import get_redis


@pytest.fixture
def buffer_service():
    """Create a RedisBufferService instance for testing."""
    return RedisBufferService(buffer_size=5)  # Use small buffer for testing


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("app.utils.redis_client.get_redis") as mock_get_redis:
        mock_redis_client = AsyncMock()
        mock_get_redis.return_value = mock_redis_client
        yield mock_redis_client


@pytest.fixture
def sample_chunks():
    """Generate sample transcript chunks for testing."""
    return [
        {"timestamp": 1, "text": "Hello everyone"},
        {"timestamp": 2, "text": "Let's start the meeting"},
        {"timestamp": 3, "text": "Today we'll discuss"},
        {"timestamp": 4, "text": "The agenda items"},
        {"timestamp": 5, "text": "First topic: Project X"},
        {"timestamp": 6, "text": "Second topic: Budget"},
    ]


class TestRedisBufferService:
    """Test suite for RedisBufferService."""

    async def test_add_chunk_basic(self, buffer_service, mock_redis, sample_chunks):
        """Test basic chunk addition."""
        meeting_id = "test-meeting"
        chunk = sample_chunks[0]
        
        await buffer_service.add_chunk(meeting_id, chunk)
        
        mock_redis.rpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()

    async def test_add_chunk_multiple(self, buffer_service, mock_redis, sample_chunks):
        """Test adding multiple chunks and buffer size management."""
        meeting_id = "test-meeting"
        
        for chunk in sample_chunks[:5]:  # First 5 chunks
            await buffer_service.add_chunk(meeting_id, chunk)
        
        # Verify buffer size is maintained
        mock_redis.ltrim.assert_called_with(
            f"transcript_buffer:{meeting_id}", -5, -1
        )

    async def test_get_recent_chunks_basic(self, buffer_service, mock_redis, sample_chunks):
        """Test basic chunk retrieval."""
        meeting_id = "test-meeting"
        
        # Mock Redis to return sample chunks
        mock_redis.lrange.return_value = sample_chunks[:3]
        
        chunks = await buffer_service.get_recent_chunks(meeting_id, count=3)
        
        assert len(chunks) == 3
        assert chunks == list(reversed(sample_chunks[:3]))
        mock_redis.lrange.assert_called_with(
            f"transcript_buffer:{meeting_id}", -3, -1
        )

    async def test_get_recent_chunks_empty(self, buffer_service, mock_redis):
        """Test retrieval when buffer is empty."""
        meeting_id = "test-meeting"
        
        mock_redis.lrange.return_value = []
        
        chunks = await buffer_service.get_recent_chunks(meeting_id, count=10)
        
        assert chunks == []
        mock_redis.lrange.assert_called_with(
            f"transcript_buffer:{meeting_id}", -10, -1
        )

    async def test_clear_buffer(self, buffer_service, mock_redis):
        """Test buffer clearing."""
        meeting_id = "test-meeting"
        
        await buffer_service.clear_buffer(meeting_id)
        
        mock_redis.delete.assert_called_once_with(
            f"transcript_buffer:{meeting_id}"
        )

    async def test_get_buffer_size(self, buffer_service, mock_redis):
        """Test buffer size retrieval."""
        meeting_id = "test-meeting"
        
        mock_redis.llen.return_value = 3
        
        size = await buffer_service.get_buffer_size(meeting_id)
        
        assert size == 3
        mock_redis.llen.assert_called_once_with(
            f"transcript_buffer:{meeting_id}"
        )

    async def test_get_all_meeting_ids(self, buffer_service, mock_redis):
        """Test retrieval of all meeting IDs."""
        
        # Mock Redis to return some keys
        mock_redis.keys.return_value = [
            "transcript_buffer:meeting1",
            "transcript_buffer:meeting2",
            "transcript_buffer:meeting3"
        ]
        
        meeting_ids = await buffer_service.get_all_meeting_ids()
        
        assert meeting_ids == ["meeting1", "meeting2", "meeting3"]
        mock_redis.keys.assert_called_once_with("transcript_buffer:*")

    async def test_cleanup_old_buffers(self, buffer_service, mock_redis):
        """Test buffer cleanup functionality."""
        
        # Mock Redis to return some keys with chunks
        mock_redis.keys.return_value = ["transcript_buffer:old1", "transcript_buffer:old2"]
        
        # Mock chunks with timestamps
        mock_redis.lindex.side_effect = [
            {"timestamp": 1000},  # Old chunk
            None  # No chunk
        ]
        
        cleaned_count = await buffer_service.cleanup_old_buffers(max_age_seconds=500)
        
        assert cleaned_count == 1
        mock_redis.delete.assert_called_once_with("transcript_buffer:old1")

    async def test_error_handling_add_chunk(self, buffer_service, mock_redis):
        """Test error handling during chunk addition."""
        meeting_id = "test-meeting"
        chunk = {"timestamp": 1, "text": "Test"}
        
        # Mock Redis to raise an exception
        mock_redis.rpush.side_effect = Exception("Redis error")
        
        # Should not raise, just log the error
        await buffer_service.add_chunk(meeting_id, chunk)

    async def test_error_handling_get_chunks(self, buffer_service, mock_redis):
        """Test error handling during chunk retrieval."""
        meeting_id = "test-meeting"
        
        # Mock Redis to raise an exception
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        chunks = await buffer_service.get_recent_chunks(meeting_id, count=10)
        
        assert chunks == []

    async def test_error_handling_clear_buffer(self, buffer_service, mock_redis):
        """Test error handling during buffer clearing."""
        meeting_id = "test-meeting"
        
        # Mock Redis to raise an exception
        mock_redis.delete.side_effect = Exception("Redis error")
        
        # Should not raise, just log the error
        await buffer_service.clear_buffer(meeting_id)

    async def test_error_handling_get_size(self, buffer_service, mock_redis):
        """Test error handling during buffer size retrieval."""
        meeting_id = "test-meeting"
        
        # Mock Redis to raise an exception
        mock_redis.llen.side_effect = Exception("Redis error")
        
        size = await buffer_service.get_buffer_size(meeting_id)
        
        assert size == 0

    async def test_singleton_instance(self):
        """Test that the singleton instance works correctly."""
        from app.services.redis_buffer_service import buffer_service
        
        assert buffer_service is not None
        assert isinstance(buffer_service, RedisBufferService)

    async def test_convenience_functions(self, buffer_service, mock_redis):
        """Test the convenience functions work with the singleton."""
        meeting_id = "test-meeting"
        chunk = {"timestamp": 1, "text": "Test"}
        
        # Mock the singleton methods
        with patch("app.services.redis_buffer_service.buffer_service", buffer_service):
            await add_chunk(meeting_id, chunk)
            chunks = await get_recent_chunks(meeting_id)
            await clear_buffer(meeting_id)
            size = await get_buffer_size(meeting_id)
        
        # Verify methods were called
        buffer_service.add_chunk.assert_called_once_with(meeting_id, chunk)
        buffer_service.get_recent_chunks.assert_called_once_with(meeting_id)
        buffer_service.clear_buffer.assert_called_once_with(meeting_id)
        buffer_service.get_buffer_size.assert_called_once_with(meeting_id)


# Integration test to verify actual Redis operations
@pytest.mark.asyncio
async def test_integration_redis_operations():
    """Integration test to verify Redis operations work end-to-end."""
    
    # Create a real service instance
    service = RedisBufferService(buffer_size=3)
    meeting_id = "integration-test"
    
    # Add some chunks
    chunk1 = {"timestamp": 1, "text": "First"}
    chunk2 = {"timestamp": 2, "text": "Second"}
    chunk3 = {"timestamp": 3, "text": "Third"}
    chunk4 = {"timestamp": 4, "text": "Fourth"}  # This should push out the first chunk
    
    await service.add_chunk(meeting_id, chunk1)
    await service.add_chunk(meeting_id, chunk2)
    await service.add_chunk(meeting_id, chunk3)
    await service.add_chunk(meeting_id, chunk4)
    
    # Get recent chunks (should be 3 most recent)
    chunks = await service.get_recent_chunks(meeting_id, count=3)
    
    assert len(chunks) == 3
    assert chunks[0]["text"] == "Fourth"
    assert chunks[1]["text"] == "Third"
    assert chunks[2]["text"] == "Second"
    
    # Clear buffer
    await service.clear_buffer(meeting_id)
    
    # Verify buffer is empty
    size = await service.get_buffer_size(meeting_id)
    assert size == 0


if __name__ == "__main__":
    # Run tests directly if executed as a script
    pytest.main([__file__, "-v"])


# Test configuration for pytest
def pytest_configure(config):
    """Configure pytest for Redis buffer service tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark tests that require actual Redis connection"
    )