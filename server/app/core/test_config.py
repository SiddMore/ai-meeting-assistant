"""
Test configuration for Socket.IO Redis integration tests.
"""

from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    SENDGRID_API_KEY: str = "test_sendgrid_key"
    ALLOWED_ORIGINS: str = "*"
    DEBUG: bool = True
    REDIS_URL: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env.test"
        extra = "allow"


settings = TestSettings()