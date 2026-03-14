"""
Test suite for error handling and edge cases.
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import List

from app.api.routes.catch_me_up import router
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.schemas.meeting import TranscriptChunkOut
from app.api.deps import get_current_user
from app.db.session import get_db

from conftest import (
    sample_meeting, sample_user, sample_transcript_chunks,
    mock_redis, mock_session, mock_current_user, mock_redis_buffer_service
)


class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.fixture
    def invalid_meeting_id(self):
        """Create an invalid meeting ID."""
        return "invalid-meeting-id"

    @pytest.fixture
    def expired_token(self):
        """Create an expired token."""
        return "expired_token_123"

    @pytest.fixture
    def invalid_token(self):
        """Create an invalid token."""
        return "invalid_token_456"

    @pytest.fixture
    def large_chunk_count(self):
        """Create a large chunk count."""
        return 10000

    @pytest.fixture
    def empty_transcript_chunks(self):
        """Create empty transcript chunks."""
        return []

    @pytest.fixture
    def malformed_transcript_chunk(self):
        """Create a malformed transcript chunk."""
        return {"invalid_field": "value"}

    async def test_invalid_meeting_id_format(self, mock_redis, mock_session, mock_current_user,
                                           sample_meeting):
        """Test with invalid meeting ID format."""
        invalid_meeting_id = self.invalid_meeting_id
        user = sample_user

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{invalid_meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 422  # Unprocessable Entity

    async def test_expired_token(self, mock_redis, mock_session, mock_current_user,
                               sample_meeting, sample_transcript_chunks):
        """Test with expired token."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user to return None (expired token)
        mock_current_user.return_value = None

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 401  # Unauthorized

    async def test_invalid_token(self, mock_redis, mock_session, mock_current_user,
                               sample_meeting, sample_transcript_chunks):
        """Test with invalid token."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user to return None (invalid token)
        mock_current_user.return_value = None

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 401  # Unauthorized

    async def test_large_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                  sample_meeting, sample_transcript_chunks):
        """Test with excessively large chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = self.large_chunk_count

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                chunk_count=chunk_count,
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 422  # Unprocessable Entity

    async def test_empty_transcript_chunks(self, mock_redis, mock_session, mock_current_user,
                                         sample_meeting):
        """Test with empty transcript chunks."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data to be empty
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions
        assert response.status_code == 200
        assert response.json()["chunks"] == []
        assert response.json()["total_chunks"] == 0

    async def test_malformed_transcript_chunk(self, mock_redis, mock_session, mock_current_user,
                                            sample_meeting):
        """Test with malformed transcript chunk."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        malformed_chunk = self.malformed_transcript_chunk

        # Mock Redis buffer data with malformed chunk
        mock_redis.lrange.return_value = [str(malformed_chunk).encode()]
        mock_redis.llen.return_value = 1

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_missing_required_fields(self, mock_redis, mock_session, mock_current_user,
                                         sample_meeting):
        """Test with missing required fields."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with missing fields
        mock_redis.lrange.return_value = [str({}).encode()]
        mock_redis.llen.return_value = 1

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_invalid_timestamp_format(self, mock_redis, mock_session, mock_current_user,
                                          sample_meeting, sample_transcript_chunks):
        """Test with invalid timestamp format."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with invalid timestamp
        invalid_chunks = [
            {"timestamp": "invalid", "text": "Test text"} for _ in sample_transcript_chunks[:5]
        ]
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in invalid_chunks
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_negative_timestamp(self, mock_redis, mock_session, mock_current_user,
                                   sample_meeting, sample_transcript_chunks):
        """Test with negative timestamp."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with negative timestamp
        negative_chunks = [
            {"timestamp": -1, "text": "Test text"} for _ in sample_transcript_chunks[:5]
        ]
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in negative_chunks
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_future_timestamp(self, mock_redis, mock_session, mock_current_user,
                                  sample_meeting, sample_transcript_chunks):
        """Test with future timestamp."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with future timestamp
        future_chunks = [
            {"timestamp": 999999999, "text": "Test text"} for _ in sample_transcript_chunks[:5]
        ]
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in future_chunks
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_duplicate_chunks(self, mock_redis, mock_session, mock_current_user,
                                  sample_meeting, sample_transcript_chunks):
        """Test with duplicate chunks."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with duplicate chunks
        duplicate_chunks = sample_transcript_chunks[:3] * 2  # Duplicate first 3 chunks
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in duplicate_chunks
        ]
        mock_redis.llen.return_value = len(duplicate_chunks)

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions - should handle duplicates gracefully
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == len(duplicate_chunks)

    async def test_out_of_order_chunks(self, mock_redis, mock_session, mock_current_user,
                                     sample_meeting, sample_transcript_chunks):
        """Test with out-of-order chunks."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with out-of-order chunks
        out_of_order_chunks = [
            sample_transcript_chunks[2],  # timestamp 3
            sample_transcript_chunks[0],  # timestamp 1
            sample_transcript_chunks[1],  # timestamp 2
        ]
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in out_of_order_chunks
        ]
        mock_redis.llen.return_value = len(out_of_order_chunks)

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions - should handle out-of-order chunks gracefully
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == len(out_of_order_chunks)

    async def test_corrupted_data(self, mock_redis, mock_session, mock_current_user,
                                sample_meeting):
        """Test with corrupted data in Redis."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with corrupted data
        mock_redis.lrange.return_value = [b"corrupted_data"]
        mock_redis.llen.return_value = 1

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_partial_data(self, mock_redis, mock_session, mock_current_user,
                              sample_meeting):
        """Test with partial data in Redis."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with partial data
        mock_redis.lrange.return_value = [b"{\"timestamp\": 1}"]  # Missing text field
        mock_redis.llen.return_value = 1

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_database_connection_error(self, mock_redis, mock_session, mock_current_user,
                                           sample_meeting, sample_transcript_chunks):
        """Test database connection error."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query to raise an exception
        mock_session.execute.side_effect = Exception("Database connection error")

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_redis_connection_error(self, mock_redis, mock_session, mock_current_user,
                                        sample_meeting):
        """Test Redis connection error."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis to raise an exception
        mock_redis.lrange.side_effect = Exception("Redis connection error")

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 500  # Internal Server Error

    async def test_concurrent_requests(self, mock_redis, mock_session, mock_current_user,
                                     sample_meeting, sample_transcript_chunks):
        """Test concurrent requests handling."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Simulate concurrent requests
        import asyncio
        
        async def make_request():
            return await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        # Create multiple concurrent requests
        tasks = [make_request() for _ in range(5)]
        
        # Run concurrent requests
        results = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for result in results:
            assert result.status_code == 200

    async def test_rate_limiting(self, mock_redis, mock_session, mock_current_user,
                               sample_meeting, sample_transcript_chunks):
        """Test rate limiting."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Simulate rapid consecutive requests
        import time
        
        start_time = time.time()
        
        # Make multiple requests in quick succession
        for _ in range(10):
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            assert response.status_code == 200
        
        end_time = time.time()
        
        # Verify requests were processed quickly (no artificial delay)
        assert end_time - start_time < 1.0  # Should complete within 1 second