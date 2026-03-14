import uuid
from datetime import datetime
from sqlalchemy import DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.session import Base


class MOM(Base):
    __tablename__ = "moms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # LLM-generated content
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_decisions: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # full MOM markdown

    # Vector embeddings for semantic search
    content_vector: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Storage
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Email dispatch
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="mom")
    action_items: Mapped[list["ActionItem"]] = relationship("ActionItem", back_populates="mom", cascade="all, delete-orphan")
