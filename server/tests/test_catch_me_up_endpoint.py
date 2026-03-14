"""
Test suite for Catch-Me-Up API endpoint.
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


class TestCatchMeUpEndpoint:
    """Test suite for Catch-Me-Up API endpoint."""

    @pytest.fixture
    def catch_me_up_response(self):
        """Create a sample CatchMeUpResponse."""
        class CatchMeUpResponse:
            def __init__(self, meeting_id, chunks, total_chunks, buffer_size, timestamp):
                self.meeting_id = meeting_id
                self.chunks = chunks
                self.total_chunks = total_chunks
                self.buffer_size = buffer_size
                self.timestamp = timestamp
        return CatchMeUpResponse

    @pytest.fixture
    def transcript_chunk_out(self):
        """Create a sample TranscriptChunkOut."""
        class TranscriptChunkOut:
            def __init__(self, timestamp, text, speaker=None, confidence=None):
                self.timestamp = timestamp
                self.text = text
                self.speaker = speaker
                self.confidence = confidence
        return TranscriptChunkOut

    async def test_catch_me_up_basic(self, mock_redis, mock_session, mock_current_user,
                                   sample_meeting, sample_transcript_chunks):
        """Test basic catch-me-up functionality."""
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

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            chunk_count=5,
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions
        assert response.status_code == 200
        assert response.json()["meeting_id"] == str(meeting_id)
        assert len(response.json()["chunks"]) == 5
        assert response.json()["total_chunks"] == 5
        assert response.json()["buffer_size"] > 0

    async def test_catch_me_up_with_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                             sample_meeting, sample_transcript_chunks):
        """Test catch-me-up with custom chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = 3

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:chunk_count]
        ]
        mock_redis.llen.return_value = chunk_count

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            chunk_count=chunk_count,
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == chunk_count

    async def test_catch_me_up_meeting_not_found(self, mock_redis, mock_session, mock_current_user,
                                              sample_meeting):
        """Test catch-me-up when meeting is not found."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock database query to return None
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 404

    async def test_catch_me_up_unauthorized_access(self, mock_redis, mock_session, mock_current_user,
                                                sample_meeting, sample_transcript_chunks):
        """Test catch-me-up with unauthorized access."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user to return None (unauthorized)
        mock_current_user.return_value = None

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        assert exc_info.value.status_code == 401

    async def test_catch_me_up_redis_error(self, mock_redis, mock_session, mock_current_user,
                                         sample_meeting, sample_transcript_chunks):
        """Test catch-me-up when Redis returns an error."""
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

        assert exc_info.value.status_code == 500

    async def test_catch_me_up_empty_buffer(self, mock_redis, mock_session, mock_current_user,
                                          sample_meeting):
        """Test catch-me-up when Redis buffer is empty."""
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

    async def test_catch_me_up_large_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                              sample_meeting, sample_transcript_chunks):
        """Test catch-me-up with large chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = 1000

        # Mock Redis buffer data with more chunks than requested
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:10]
        ]
        mock_redis.llen.return_value = 10

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            chunk_count=chunk_count,
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == 10  # Only 10 available

    async def test_catch_me_up_with_timestamp(self, mock_redis, mock_session, mock_current_user,
                                            sample_meeting, sample_transcript_chunks):
        """Test catch-me-up includes timestamp in response."""
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

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions
        assert response.status_code == 200
        assert "timestamp" in response.json()
        assert isinstance(response.json()["timestamp"], str)

    async def test_catch_me_up_response_structure(self, mock_redis, mock_session, mock_current_user,
                                               sample_meeting, sample_transcript_chunks):
        """Test catch-me-up response structure."""
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

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Assertions for response structure
        response_data = response.json()
        assert "meeting_id" in response_data
        assert "chunks" in response_data
        assert "total_chunks" in response_data
        assert "buffer_size" in response_data
        assert "timestamp" in response_data

        # Check chunk structure
        for chunk in response_data["chunks"]:
            assert "timestamp" in chunk
            assert "text" in chunk
            assert "speaker" in chunk or chunk["speaker"] is None
            assert "confidence" in chunk or chunk["confidence"] is None

    async def test_catch_me_up_with_invalid_meeting_id(self, mock_redis, mock_session, mock_current_user):
        """Test catch-me-up with invalid meeting ID format."""
        invalid_meeting_id = "invalid-meeting-id"
        user = sample_user

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

    async def test_catch_me_up_with_negative_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                                       sample_meeting):
        """Test catch-me-up with negative chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = -5

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

    async def test_catch_me_up_with_zero_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                                   sample_meeting):
        """Test catch-me-up with zero chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = 0

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

    async def test_catch_me_up_with_excessive_chunk_count(self, mock_redis, mock_session, mock_current_user,
                                                        sample_meeting):
        """Test catch-me-up with excessive chunk count."""
        meeting_id = sample_meeting["id"]
        user = sample_user
        chunk_count = 10000  # Exceeds maximum allowed

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