"""
redis_buffer_service.py — High-performance Redis-based rolling buffer for transcript chunks.

Provides a thread-safe, async Redis-backed buffer for storing and retrieving transcript chunks
with configurable size limits and meeting-specific isolation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.utils.redis_client import get_redis

log = logging.getLogger(__name__)


class RedisBufferService:
    """High-performance Redis-based rolling buffer for transcript chunks."""

    def __init__(self, buffer_size: int = 100):
        """
        Initialize the buffer service with configurable size.
        
        Args:
            buffer_size: Maximum number of chunks to keep in the buffer (default: 100)
        """
        self.buffer_size = buffer_size
        self.redis_key_prefix = "transcript_buffer:"

    async def _get_redis_key(self, meeting_id: str) -> str:
        """Generate the Redis key for a specific meeting."""
        return f"{self.redis_key_prefix}{meeting_id}"

    async def add_chunk(self, meeting_id: str, chunk_data: Dict[str, Any]) -> None:
        """
        Add a transcript chunk to the buffer for a specific meeting.
        
        Args:
            meeting_id: Unique identifier for the meeting
            chunk_data: Dictionary containing chunk information (timestamp, text, etc.)
        """
        try:
            redis_key = await self._get_redis_key(meeting_id)
            async with get_redis() as r:
                # Use Redis list operations for efficient FIFO behavior
                await r.rpush(redis_key, chunk_data)
                
                # Trim the list to maintain buffer size
                await r.ltrim(redis_key, -self.buffer_size, -1)
                
        except Exception as e:
            log.error(f"Failed to add chunk to buffer for meeting {meeting_id}: {e}")
            # Consider implementing retry logic or fallback storage here

    async def get_recent_chunks(self, meeting_id: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent transcript chunks for a specific meeting.
        
        Args:
            meeting_id: Unique identifier for the meeting
            count: Number of recent chunks to retrieve (default: 100)
            
        Returns:
            List of recent transcript chunks, most recent first
        """
        try:
            redis_key = await self._get_redis_key(meeting_id)
            async with get_redis() as r:
                # Get the last 'count' items from the list
                chunks = await r.lrange(redis_key, -count, -1)
                
                # Reverse to return most recent first
                return list(reversed(chunks))
                
        except Exception as e:
            log.error(f"Failed to get recent chunks for meeting {meeting_id}: {e}")
            return []

    async def clear_buffer(self, meeting_id: str) -> None:
        """
        Clear all chunks from the buffer for a specific meeting.
        
        Args:
            meeting_id: Unique identifier for the meeting
        """
        try:
            redis_key = await self._get_redis_key(meeting_id)
            async with get_redis() as r:
                await r.delete(redis_key)
                
        except Exception as e:
            log.error(f"Failed to clear buffer for meeting {meeting_id}: {e}")

    async def get_buffer_size(self, meeting_id: str) -> int:
        """
        Get the current number of chunks in the buffer for a specific meeting.
        
        Args:
            meeting_id: Unique identifier for the meeting
            
        Returns:
            Number of chunks currently in the buffer
        """
        try:
            redis_key = await self._get_redis_key(meeting_id)
            async with get_redis() as r:
                return await r.llen(redis_key)
                
        except Exception as e:
            log.error(f"Failed to get buffer size for meeting {meeting_id}: {e}")
            return 0

    async def get_all_meeting_ids(self) -> List[str]:
        """
        Get a list of all meeting IDs that currently have buffers.
        
        Returns:
            List of meeting IDs with active buffers
        """
        try:
            async with get_redis() as r:
                keys = await r.keys(f"{self.redis_key_prefix}*")
                # Extract meeting IDs from keys
                return [key.split(':')[-1] for key in keys]
                
        except Exception as e:
            log.error(f"Failed to get all meeting IDs: {e}")
            return []

    async def cleanup_old_buffers(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up buffers that haven't been updated in a while.
        
        Args:
            max_age_seconds: Maximum age in seconds before buffer is considered stale
            
        Returns:
            Number of buffers cleaned up
        """
        try:
            async with get_redis() as r:
                keys = await r.keys(f"{self.redis_key_prefix}*")
                cleaned_count = 0
                
                for key in keys:
                    # Check last access time (approximate using last element timestamp)
                    last_chunk = await r.lindex(key, -1)
                    if last_chunk:
                        # Assuming chunk has a 'timestamp' field
                        last_timestamp = last_chunk.get('timestamp', 0)
                        if (asyncio.get_event_loop().time() - last_timestamp) > max_age_seconds:
                            await r.delete(key)
                            cleaned_count += 1
                
                return cleaned_count
                
        except Exception as e:
            log.error(f"Failed to cleanup old buffers: {e}")
            return 0


# Singleton instance for easy import
buffer_service = RedisBufferService()


# Convenience functions for direct use
async def add_chunk(meeting_id: str, chunk_data: Dict[str, Any]) -> None:
    """Convenience function to add a chunk using the default buffer service."""
    await buffer_service.add_chunk(meeting_id, chunk_data)


async def get_recent_chunks(meeting_id: str, count: int = 100) -> List[Dict[str, Any]]:
    """Convenience function to get recent chunks using the default buffer service."""
    return await buffer_service.get_recent_chunks(meeting_id, count)


async def clear_buffer(meeting_id: str) -> None:
    """Convenience function to clear buffer using the default buffer service."""
    await buffer_service.clear_buffer(meeting_id)


async def get_buffer_size(meeting_id: str) -> int:
    """Convenience function to get buffer size using the default buffer service."""
    return await buffer_service.get_buffer_size(meeting_id)