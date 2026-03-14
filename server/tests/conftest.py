"""
Pytest configuration for comprehensive test suite.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import uuid
import os

# Import test settings
from app.core.test_config import settings

# Configure test environment
os.environ["TESTING"] = "true"

# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create a new event loop for each test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings():
    """Provide test settings configuration."""
    return settings

@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client for testing."""
    with patch("app.utils.redis_client.get_redis") as mock_get_redis:
        mock_redis_client = AsyncMock()
        mock_get_redis.return_value = mock_redis_client
        yield mock_redis_client

@pytest.fixture(scope="function")
def sample_meeting():
    """Generate a sample meeting for testing."""
    return {
        "id": uuid.uuid4(),
        "title": "Test Meeting",
        "description": "Test meeting description",
        "start_time": datetime.now(timezone.utc),
        "end_time": None,
        "status": "scheduled",
        "created_by": uuid.uuid4(),
        "bot_status": "not_started",
        "language": "en"
    }

@pytest.fixture(scope="function")
def sample_user():
    """Generate a sample user for testing."""
    return {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "name": "Test User",
        "is_active": True
    }

@pytest.fixture(scope="function")
def sample_transcript_chunks():
    """Generate sample transcript chunks for testing."""
    return [
        {"timestamp": 1, "text": "Hello everyone"},
        {"timestamp": 2, "text": "Let's start the meeting"},
        {"timestamp": 3, "text": "Today we'll discuss"},
        {"timestamp": 4, "text": "The agenda items"},
        {"timestamp": 5, "text": "First topic: Project X"},
        {"timestamp": 6, "text": "Second topic: Budget"},
        {"timestamp": 7, "text": "Any questions?"},
        {"timestamp": 8, "text": "Great, let's wrap up"},
    ]

@pytest.fixture(scope="function")
def sample_error_chunks():
    """Generate sample error chunks for testing."""
    return [
        {"timestamp": 1, "text": "Error: Connection lost"},
        {"timestamp": 2, "text": "Warning: Audio quality low"},
        {"timestamp": 3, "text": "Critical: Bot failed to join"},
    ]

@pytest.fixture(scope="function")
def mock_socketio():
    """Create a mock Socket.IO server instance."""
    with patch("app.realtime.socketio_server.create_sio_server") as mock_create_sio:
        mock_sio = AsyncMock()
        mock_create_sio.return_value = mock_sio
        yield mock_sio

@pytest.fixture(scope="function")
def mock_session():
    """Create a mock database session."""
    with patch("app.db.session.get_db") as mock_get_db:
        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session
        yield mock_session

@pytest.fixture(scope="function")
def mock_current_user():
    """Create a mock current user dependency."""
    with patch("app.api.deps.get_current_user") as mock_get_user:
        mock_user = AsyncMock()
        mock_get_user.return_value = mock_user
        yield mock_user

@pytest.fixture(scope="function")
def mock_redis_buffer_service():
    """Create a mock Redis buffer service."""
    with patch("app.services.redis_buffer_service.RedisBufferService") as mock_service:
        mock_instance = AsyncMock()
        mock_service.return_value = mock_instance
        yield mock_instance

@pytest.fixture(scope="function")
def performance_test_settings():
    """Performance testing configuration."""
    return {
        "chunk_count": 1000,
        "concurrent_users": 50,
        "test_duration": 60,  # seconds
        "buffer_size": 10000
    }

@pytest.fixture(scope="function")
def security_test_settings():
    """Security testing configuration."""
    return {
        "auth_tokens": ["valid_token", "expired_token", "invalid_token"],
        "user_roles": ["admin", "user", "guest"],
        "permission_levels": ["read", "write", "admin"]
    }

@pytest.fixture(scope="function")
def test_data_factory():
    """Factory for creating test data."""
    class TestDataFactory:
        @staticmethod
        def create_meeting(**kwargs):
            meeting = {
                "id": uuid.uuid4(),
                "title": "Test Meeting",
                "description": "Test meeting description",
                "start_time": datetime.now(timezone.utc),
                "end_time": None,
                "status": "scheduled",
                "created_by": uuid.uuid4(),
                "bot_status": "not_started",
                "language": "en"
            }
            meeting.update(kwargs)
            return meeting

        @staticmethod
        def create_user(**kwargs):
            user = {
                "id": uuid.uuid4(),
                "email": "test@example.com",
                "name": "Test User",
                "is_active": True
            }
            user.update(kwargs)
            return user

        @staticmethod
        def create_transcript_chunk(**kwargs):
            chunk = {
                "timestamp": 1,
                "text": "Test transcript text",
                "speaker": "Test Speaker",
                "confidence": 0.95
            }
            chunk.update(kwargs)
            return chunk

    return TestDataFactory()

@pytest.fixture(scope="function")
def mock_external_services():
    """Mock external services for testing."""
    with patch("app.services.bot_service.BotService") as mock_bot_service,
         patch("app.services.email_service.EmailService") as mock_email_service,
         patch("app.services.calendar_service.CalendarService") as mock_calendar_service:
        yield {
            "bot_service": mock_bot_service,
            "email_service": mock_email_service,
            "calendar_service": mock_calendar_service
        }

@pytest.fixture(scope="function")
def mock_logging():
    """Mock logging for testing."""
    with patch("logging.Logger.info") as mock_info,
         patch("logging.Logger.error") as mock_error,
         patch("logging.Logger.warning") as mock_warning:
        yield {
            "info": mock_info,
            "error": mock_error,
            "warning": mock_warning
        }

@pytest.fixture(scope="function")
def mock_time():
    """Mock time-related functions for testing."""
    with patch("datetime.datetime") as mock_datetime:
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.utcnow.return_value = mock_now
        yield mock_datetime

@pytest.fixture(scope="function")
def mock_uuid():
    """Mock UUID generation for testing."""
    with patch("uuid.uuid4") as mock_uuid4:
        mock_uuid4.return_value = uuid.UUID("12345678123456781234567812345678")
        yield mock_uuid4

@pytest.fixture(scope="function")
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict("os.environ", {
        "TESTING": "true",
        "REDIS_URL": "redis://localhost:6379",
        "SENDGRID_API_KEY": "test_key"
    }, clear=True):
        yield