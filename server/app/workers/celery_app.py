from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "meeting_assistant",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.mom",  # Keep this since we just fixed mom.py
        # "app.workers.transcription",  <-- Comment these out if the files don't exist yet
        # "app.workers.translation",
        # "app.workers.llm",
        # "app.workers.email",
        # "app.workers.calendar_sync",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # re-queue on worker crash
    worker_prefetch_multiplier=1, # fair dispatch for slow AI tasks
    task_routes={
        "app.workers.transcription.*": {"queue": "transcription"},
        "app.workers.translation.*": {"queue": "transcription"},
        "app.workers.mom.*": {"queue": "ai"},
        "app.workers.llm.*": {"queue": "ai"},
        "app.workers.email.*": {"queue": "email"},
        "app.workers.calendar_sync.*": {"queue": "calendar"},
    },
)
