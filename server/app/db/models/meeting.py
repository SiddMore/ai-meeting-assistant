import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class MeetingPlatform(str, PyEnum):
    google_meet = "google_meet"
    zoom = "zoom"
    teams = "teams"
    other = "other"


class MeetingStatus(str, PyEnum):
    scheduled = "scheduled"
    bot_joining = "bot_joining"
    in_progress = "in_progress"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    platform: Mapped[MeetingPlatform] = mapped_column(Enum(MeetingPlatform), nullable=False)
    meeting_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Recall.ai bot tracking
    recall_bot_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus), default=MeetingStatus.scheduled, nullable=False
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="meetings")
    participants: Mapped[list["Participant"]] = relationship("Participant", back_populates="meeting", cascade="all, delete-orphan")
    transcript: Mapped["Transcript | None"] = relationship("Transcript", back_populates="meeting", uselist=False, lazy="selectin")
    mom: Mapped["MOM | None"] = relationship("MOM", back_populates="meeting", uselist=False)


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")
