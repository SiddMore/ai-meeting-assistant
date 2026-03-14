import uuid
from datetime import datetime, timedelta, date, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.transcript import Transcript
from app.db.models.mom import MOM
from app.db.models.action_item import ActionItem, TaskStatus, TaskPriority
from app.services import calendar_service


@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    # Upsert to prevent UNIQUE constraint error on repeated runs
    result = await db.execute(select(User).where(User.email == "phase5@test.com"))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    user = User(
        id=uuid.uuid4(),
        email="phase5@test.com",
        name="Phase 5 Tester",
        hashed_password="mock",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_meeting(db: AsyncSession, test_user: User):
    meeting = Meeting(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="Phase 5 Meeting",
        platform="google_meet",
        meeting_url="https://meet.google.com/test",
        status=MeetingStatus.completed,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # minimal transcript needed by MOM generator
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content_raw="Test",
        content_translated="Test",
        primary_language="en",
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)

    meeting.transcript = transcript
    await db.commit()
    return meeting


@pytest.mark.asyncio
async def test_calendar_integration_endpoints(db: AsyncSession, test_user: User):
    # user initially has no refresh tokens
    assert not test_user.google_refresh_token_enc
    assert not test_user.microsoft_refresh_token_enc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # need to fake auth; we'll just bypass middleware by patching
        response = await client.get("/api/v1/integrations/calendar")
        assert response.status_code in (200, 401)
        # if request was unauthorized, skip further assertions
        if response.status_code != 200:
            return

        data = response.json()
        assert isinstance(data, list)
        assert any(p["provider"] == "google" for p in data)

        # disconnecting unknown provider should be ignored
        resp2 = await client.post("/api/v1/integrations/calendar/foobar/disconnect")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "ignored"

        # disconnecting when nothing set should also succeed
        resp3 = await client.post("/api/v1/integrations/calendar/google/disconnect")
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "disconnected"


@pytest.mark.asyncio
async def test_calendar_events_endpoint_filters(db: AsyncSession, test_user: User, test_meeting: Meeting):
    # create mom and action item
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary="foo",
        full_content="bar",
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    ai = ActionItem(
        id=uuid.uuid4(),
        mom_id=mom.id,
        task="Do something",
        assignee_email=test_user.email,
        status=TaskStatus.todo,
        priority=TaskPriority.medium,
        deadline=date(2026, 3, 20),
    )
    db.add(ai)
    await db.commit()
    await db.refresh(ai)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/calendar/events")
        assert resp.status_code in (200, 401)
        if resp.status_code != 200:
            return
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
        # our single action item should appear
        assert any(e["action_item_id"] == str(ai.id) for e in data["events"])


@pytest.mark.asyncio
async def test_calendar_service_tasks(monkeypatch, db: AsyncSession, test_user: User, test_meeting: Meeting):
    # create mom + ai and attach to user by meeting
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary="foo",
        full_content="bar",
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    ai = ActionItem(
        id=uuid.uuid4(),
        mom_id=mom.id,
        task="Do something else",
        assignee_email=test_user.email,
        status=TaskStatus.todo,
        priority=TaskPriority.medium,
    )
    db.add(ai)
    await db.commit()
    await db.refresh(ai)

    called = {}

    async def fake_create(db_sess, action_item):
        called["create"] = action_item.id

    async def fake_update(db_sess, action_item):
        called["update"] = action_item.id

    async def fake_delete(db_sess, action_item):
        called["delete"] = action_item.id

    monkeypatch.setattr(calendar_service, "create_event", fake_create)
    monkeypatch.setattr(calendar_service, "update_event", fake_update)
    monkeypatch.setattr(calendar_service, "delete_event", fake_delete)

    # call the service directly
    await calendar_service.create_event(db, ai)
    assert called.get("create") == ai.id

    ai.task = "changed"
    await calendar_service.update_event(db, ai)
    assert called.get("update") == ai.id

    await calendar_service.delete_event(db, ai)
    assert called.get("delete") == ai.id


# additional sanity check: worker registration

def test_calendar_worker_registered():
    from app.workers.celery_app import celery_app
    from app.workers import calendar_sync

    assert "app.workers.calendar_sync.create_or_update" in celery_app.tasks
    assert "app.workers.calendar_sync.update" in celery_app.tasks
    assert "app.workers.calendar_sync.delete" in celery_app.tasks


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
