import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # null if OAuth-only

    # OAuth
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    microsoft_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # Encrypted OAuth refresh tokens (AES-256 Fernet)
    google_refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    microsoft_refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'google' | 'microsoft' | None

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", back_populates="owner", lazy="select")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
