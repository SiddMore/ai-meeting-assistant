# Import all models here so Alembic (and init_db) can discover them
from app.db.session import Base  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.meeting import Meeting, Participant  # noqa: F401
from app.db.models.transcript import Transcript  # noqa: F401
from app.db.models.transcript_chunk import TranscriptChunk  # noqa: F401
from app.db.models.mom import MOM  # noqa: F401
from app.db.models.action_item import ActionItem  # noqa: F401
from app.db.models.calendar_event import CalendarEvent  # noqa: F401
