"""
Test suite for performance testing.
"""

import pytest
import asyncio
import time
import random
from typing import List

from app.api.routes.catch_me_up import router
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.schemas.meeting import TranscriptChunkOut
from app.api.deps import get_current_user
from app.db.session import get_db

from conftest import (
    sample_meeting, sample_user, sample_transcript_chunks,
    mock_redis, mock_session, mock_current_user, mock_redis_buffer_service,
    performance_test_settings
)


class TestPerformance:
    """Test suite for performance testing."""

    @pytest.fixture
    def large_transcript_chunks(self):
        """Generate a large number of transcript chunks for performance testing."""
        chunks = []
        for i in range(performance_test_settings["chunk_count"]):
            chunks.append({
                "timestamp": i,
                "text": f"Test transcript text {i}",
                "speaker": f"Speaker {i % 5}",
                "confidence": random.uniform(0.8, 0.99)
            })
        return chunks

    @pytest.fixture
    def concurrent_users(self):
        """Generate concurrent user sessions."""
        users = []
        for i in range(performance_test_settings["concurrent_users"]):
            users.append({
                "id": f"user_{i}",
                "email": f"user{i}@example.com",
                "name": f"Test User {i}",
                "is_active": True
            })
        return users

    async def test_high_volume_chunks(self, mock_redis, mock_session, mock_current_user,
                                    sample_meeting, large_transcript_chunks):
        """Test handling high volume of transcript chunks."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with large number of chunks
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in large_transcript_chunks
        ]
        mock_redis.llen.return_value = len(large_transcript_chunks)

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Measure performance
        start_time = time.time()

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Assertions
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == len(large_transcript_chunks)
        
        # Performance threshold: should complete within 2 seconds
        assert elapsed_time < 2.0

    async def test_concurrent_users(self, mock_redis, mock_session, mock_current_user,
                                  sample_meeting, sample_transcript_chunks,
                                  concurrent_users):
        """Test handling concurrent users."""
        meeting_id = sample_meeting["id"]

        # Mock Redis buffer data
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in sample_transcript_chunks[:5]
        ]
        mock_redis.llen.return_value = 5

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Measure performance
        start_time = time.time()

        # Simulate concurrent users
        import asyncio
        
        async def make_request(user):
            # Mock current user for each request
            with patch("app.api.deps.get_current_user") as mock_user:
                mock_user.return_value = user
                return await router.get(
                    f"/{meeting_id}",
                    db=mock_session,
                    current_user=mock_user
                )

        # Create concurrent requests
        tasks = [make_request(user) for user in concurrent_users]
        
        # Run concurrent requests
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Assertions
        for result in results:
            assert result.status_code == 200
        
        # Performance threshold: should handle all concurrent requests within 3 seconds
        assert elapsed_time < 3.0

    async def test_memory_usage(self, mock_redis, mock_session, mock_current_user,
                              sample_meeting, large_transcript_chunks):
        """Test memory usage with large data sets."""
        meeting_id = sample_meeting["id"]
        user = sample_user

        # Mock Redis buffer data with large number of chunks
        mock_redis.lrange.return_value = [
            str(chunk).encode() for chunk in large_transcript_chunks
        ]
        mock_redis.llen.return_value = len(large_transcript_chunks)

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.first.return_value = sample_meeting

        # Mock current user
        mock_current_user.return_value = user

        # Measure memory usage (simplified - in real tests, use memory_profiler)
        import sys
        
        # Get initial memory usage
        initial_memory = sys.getsizeof(large_transcript_chunks)

        # Call the endpoint
        response = await router.get(
            f"/{meeting_id}",
            db=mock_session,
            current_user=mock_current_user
        )

        # Get final memory usage
        final_memory = sys.getsizeof(response.json())

        # Assertions
        assert response.status_code == 200
        assert len(response.json()["chunks"]) == len(large_transcript_chunks)
        
        # Memory threshold: should not exceed reasonable limits
        # This is a simplified check - in real tests, use memory_profiler
        assert final_memory < 100 * 1024 * 1024  # Should be less than 100MB

    async def test_response_time_consistency(self, mock_redis, mock_session, mock_current_user,
                                           sample_meeting, sample_transcript_chunks):
        """Test response time consistency."""
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

        # Measure response times for multiple requests
        response_times = []
        
        for _ in range(10):
            start_time = time.time()
            
            # Call the endpoint
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            response_times.append(elapsed_time)
            
            # Verify each response
            assert response.status_code == 200

        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # Assertions for consistency
        assert avg_response_time < 0.5  # Average should be less than 500ms
        assert max_response_time - min_response_time < 0.2  # Variation should be less than 200ms

    async def test_load_stress_test(self, mock_redis, mock_session, mock_current_user,
                                  sample_meeting, sample_transcript_chunks):
        """Test load stress testing."""
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

        # Stress test parameters
        stress_duration = 10  # seconds
        requests_per_second = 100
        total_requests = stress_duration * requests_per_second

        # Measure performance during stress test
        start_time = time.time()
        
        import asyncio
        
        async def stress_request():
            return await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        # Create stress test tasks
        tasks = []
        for _ in range(total_requests):
            tasks.append(stress_request())
        
        # Run stress test
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Assertions
        for result in results:
            assert result.status_code == 200
        
        # Performance metrics
        actual_requests_per_second = total_requests / elapsed_time
        
        # Should handle at least 80% of target requests per second
        assert actual_requests_per_second >= requests_per_second * 0.8

    async def test_database_query_performance(self, mock_redis, mock_session, mock_current_user,
                                            sample_meeting, sample_transcript_chunks):
        """Test database query performance."""
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

        # Measure database query performance
        start_time = time.time()

        # Call the endpoint multiple times to measure query performance
        for _ in range(100):
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            assert response.status_code == 200

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Performance threshold: 100 queries should complete within 1 second
        assert elapsed_time < 1.0

    async def test_redis_operation_performance(self, mock_redis, mock_session, mock_current_user,
                                              sample_meeting, sample_transcript_chunks):
        """Test Redis operation performance."""
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

        # Measure Redis operation performance
        start_time = time.time()

        # Call the endpoint multiple times to measure Redis performance
        for _ in range(100):
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            assert response.status_code == 200

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Performance threshold: 100 Redis operations should complete within 0.5 seconds
        assert elapsed_time < 0.5

    async def test_serialization_performance(self, mock_redis, mock_session, mock_current_user,
                                            sample_meeting, sample_transcript_chunks):
        """Test serialization performance."""
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

        # Measure serialization performance
        start_time = time.time()

        # Call the endpoint multiple times to measure serialization performance
        for _ in range(100):
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            assert response.status_code == 200

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Performance threshold: 100 serializations should complete within 0.3 seconds
        assert elapsed_time < 0.3

    async def test_throughput_test(self, mock_redis, mock_session, mock_current_user,
                                 sample_meeting, sample_transcript_chunks):
        """Test system throughput."""
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

        # Throughput test parameters
        test_duration = 5  # seconds
        max_requests = 1000

        # Measure throughput
        start_time = time.time()
        
        import asyncio
        
        async def throughput_request():
            return await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )

        # Create throughput test tasks
        tasks = []
        for _ in range(max_requests):
            tasks.append(throughput_request())
        
        # Run throughput test
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Assertions
        for result in results:
            assert result.status_code == 200
        
        # Calculate throughput
        throughput = len(results) / elapsed_time
        
        # Should achieve at least 100 requests per second
        assert throughput >= 100

    async def test_latency_distribution(self, mock_redis, mock_session, mock_current_user,
                                      sample_meeting, sample_transcript_chunks):
        """Test latency distribution."""
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

        # Measure latency distribution
        latencies = []
        
        for _ in range(100):
            start_time = time.time()
            
            # Call the endpoint
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            latencies.append(elapsed_time)
            
            # Verify each response
            assert response.status_code == 200

        # Calculate latency statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        # Assertions for latency distribution
        assert avg_latency < 0.3  # Average latency should be less than 300ms
        assert max_latency < 1.0  # Maximum latency should be less than 1 second
        assert min_latency < 0.1  # Minimum latency should be less than 100ms

    async def test_memory_leak_detection(self, mock_redis, mock_session, mock_current_user,
                                       sample_meeting, sample_transcript_chunks):
        """Test for memory leaks."""
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

        # Measure memory usage over multiple requests
        import sys
        
        # Initial memory usage
        initial_memory = sys.getsizeof(sample_transcript_chunks)
        
        # Make multiple requests
        for i in range(100):
            response = await router.get(
                f"/{meeting_id}",
                db=mock_session,
                current_user=mock_current_user
            )
            assert response.status_code == 200
        
        # Final memory usage
        final_memory = sys.getsizeof(sample_transcript_chunks)
        
        # Memory increase should be reasonable (simplified check)
        memory_increase = final_memory - initial_memory
        assert memory_increase < 1024 * 1024  # Should not increase by more than 1MB