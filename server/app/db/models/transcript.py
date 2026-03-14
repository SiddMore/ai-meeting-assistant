import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Raw transcript in original language(s)
    content_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Translated English transcript
    content_translated: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_language: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "hi", "mr", "en"

    # S3/R2 URL of the full transcript file (for large transcripts)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcript")
