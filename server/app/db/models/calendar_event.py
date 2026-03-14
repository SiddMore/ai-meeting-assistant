import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base


class CalendarProvider(str, PyEnum):
    google = "google"
    microsoft = "microsoft"


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    provider: Mapped[CalendarProvider] = mapped_column(Enum(CalendarProvider), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Google/MS event ID
    event_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    action_item: Mapped["ActionItem"] = relationship("ActionItem", back_populates="calendar_event")
