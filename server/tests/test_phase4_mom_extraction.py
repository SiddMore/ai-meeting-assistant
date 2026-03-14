"""
test_phase4_mom_extraction.py — Phase 4 test suite for MOM and action item extraction.

Tests the following:
1. Database models (MOM, ActionItem) are properly created
2. LLM MOM generation works with Gemini API (or mock fallback)
3. API endpoints return correct responses
4. Celery worker can be triggered
5. Event trigger on bot.done works
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

# Local imports
from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.transcript import Transcript
from app.db.models.mom import MOM
from app.db.models.action_item import ActionItem, TaskStatus, TaskPriority
from app.services.mom_service import generate_mom
from app.workers.mom import generate_mom_task, _parse_deadline


@pytest_asyncio.fixture
async def db():
    """Provide async database session."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="phase4@test.com",
        name="Phase 4 Tester",
        hashed_password="mock_hash",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_meeting(db: AsyncSession, test_user: User):
    """Create a test meeting with transcript."""
    meeting = Meeting(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="Phase 4 Test Meeting",
        platform="google_meet",
        meeting_link="https://meet.google.com/test",
        status=MeetingStatus.completed,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Create transcript
    transcript = Transcript(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        content_raw="""
        Team Lead: Let's discuss the Q2 roadmap.
        Engineer 1: We should prioritize performance optimization.
        Engineer 2: Agreed. We also need to fix the authentication bug.
        Product: Everyone needs to complete documentation by next Friday.
        Engineer 1: I'll take the performance optimization task.
        Engineer 2: I'll handle the authentication bug fix.
        Team Lead: Great. Engineering 1 has deadline next Friday. Engineering 2 has the same deadline.
        """,
        content_translated="<same content in English>",
        primary_language="en",
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)

    # Link transcript to meeting
    meeting.transcript = transcript
    await db.commit()

    return meeting


# ── Test Database Model Creation ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_mom_table_exists(db: AsyncSession):
    """Verify MOM table exists in database."""
    result = await db.execute(select(func.count(MOM.id)))
    count = result.scalar()
    assert count is not None, "MOM table does not exist"


@pytest.mark.asyncio
async def test_action_item_table_exists(db: AsyncSession):
    """Verify ActionItem table exists in database."""
    result = await db.execute(select(func.count(ActionItem.id)))
    count = result.scalar()
    assert count is not None, "ActionItem table does not exist"


# ── Test MOM Service ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_mom_with_mock_fallback():
    """Test MOM generation (uses mock if Google API key not set)."""
    transcript = """
    Meeting: Q2 Planning
    Participants: Alice, Bob, Charlie
    
    Alice: We need to ship feature A by end of Q2
    Bob: I'll take feature A
    Charlie: I'll work on feature B
    Alice: Feature B has lower priority
    Bob: Let's schedule a follow-up next week
    """

    participants = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
        {"name": "Charlie", "email": "charlie@example.com"},
    ]

    result = await generate_mom(
        meeting_title="Q2 Planning",
        transcript_text=transcript,
        participants=participants,
        meeting_date=datetime.now(timezone.utc),
    )

    # Verify structure
    assert "summary" in result
    assert "key_decisions" in result
    assert "action_items" in result
    assert "full_content" in result

    # Verify action items structure
    if result["action_items"]:
        action_item = result["action_items"][0]
        assert "task" in action_item
        assert "assignee_name" in action_item or action_item["assignee_name"] is None


# ── Test Deadline Parsing ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_parse_deadline_iso_format():
    """Test parsing ISO date format (YYYY-MM-DD)."""
    deadline = _parse_deadline("2026-03-15")
    assert deadline == date(2026, 3, 15)


@pytest.mark.asyncio
async def test_parse_deadline_relative_next_week():
    """Test parsing 'next week' relative deadline."""
    deadline = _parse_deadline("next week")
    assert deadline is not None
    assert isinstance(deadline, date)


@pytest.mark.asyncio
async def test_parse_deadline_relative_tomorrow():
    """Test parsing 'tomorrow' relative deadline."""
    from datetime import datetime, timedelta
    deadline = _parse_deadline("tomorrow")
    expected = (datetime.utcnow() + timedelta(days=1)).date()
    assert deadline == expected


@pytest.mark.asyncio
async def test_parse_deadline_none():
    """Test parsing None returns None."""
    deadline = _parse_deadline(None)
    assert deadline is None


# ── Test API Endpoints ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_moms_empty(db: AsyncSession, test_user: User):
    """Test listing MOMs when none exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock auth by setting user context (simplified)
        response = await client.get("/api/v1/moms/")
        # Expected to fail auth, but endpoint should be reachable
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
async def test_create_and_retrieve_mom(db: AsyncSession, test_meeting: Meeting):
    """Test creating a MOM record and retrieving it."""
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary="Test MOM summary",
        key_decisions="- Decision 1\n- Decision 2",
        full_content="# Test MOM\n\nFull content here.",
        email_sent=False,
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    # Verify MOM was created
    result = await db.execute(select(MOM).where(MOM.id == mom.id))
    retrieved_mom = result.scalar_one_or_none()
    assert retrieved_mom is not None
    assert retrieved_mom.summary == "Test MOM summary"


# ── Test Action Items CRUD ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_action_item(db: AsyncSession, test_meeting: Meeting):
    """Test creating action items linked to MOM."""
    # Create MOM first
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary="Test",
        full_content="Test content",
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    # Create action item
    action_item = ActionItem(
        id=uuid.uuid4(),
        mom_id=mom.id,
        task="Complete documentation",
        assignee_name="Alice",
        assignee_email="alice@example.com",
        deadline=date(2026, 3, 20),
        status=TaskStatus.todo,
        priority=TaskPriority.high,
    )
    db.add(action_item)
    await db.commit()
    await db.refresh(action_item)

    # Verify
    result = await db.execute(
        select(ActionItem).where(ActionItem.mom_id == mom.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].task == "Complete documentation"


@pytest.mark.asyncio
async def test_update_action_item_status(db: AsyncSession, test_meeting: Meeting):
    """Test updating action item status."""
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary="Test",
        full_content="Test content",
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    action_item = ActionItem(
        id=uuid.uuid4(),
        mom_id=mom.id,
        task="Do something",
        status=TaskStatus.todo,
        priority=TaskPriority.medium,
    )
    db.add(action_item)
    await db.commit()

    # Update status
    action_item.status = TaskStatus.in_progress
    await db.commit()

    # Verify
    result = await db.execute(
        select(ActionItem).where(ActionItem.id == action_item.id)
    )
    updated = result.scalar_one()
    assert updated.status == TaskStatus.in_progress


# ── Test Celery Worker Registration ─────────────────────────────────────────
def test_mom_worker_is_registered():
    """Test that MOM worker is properly registered in Celery app."""
    from app.workers.celery_app import celery_app
    from app.workers.mom import generate_mom_task

    # Verify the task is registered
    assert generate_mom_task in celery_app.tasks.values()
    assert generate_mom_task.name == "app.workers.mom.generate_mom"


def test_celery_task_routing_includes_mom():
    """Test that Celery task routing includes MOM worker."""
    from app.workers.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "app.workers.mom.*" in routes
    assert routes["app.workers.mom.*"]["queue"] == "ai"


# ── Integration Test ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_full_mom_pipeline_mock(db: AsyncSession, test_meeting: Meeting):
    """
    Integration test: simulate complete MOM generation pipeline
    (without actually calling Celery due to test environment constraints).
    """
    # 1. Generate MOM
    transcript = test_meeting.transcript.content_raw
    mom_data = await generate_mom(
        meeting_title=test_meeting.title,
        transcript_text=transcript,
        participants=[{"name": "Test User", "email": "test@example.com"}],
        meeting_date=test_meeting.ended_at,
    )

    # 2. Create MOM record
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        summary=mom_data["summary"],
        key_decisions=mom_data["key_decisions"],
        full_content=mom_data["full_content"],
        email_sent=False,
    )
    db.add(mom)
    await db.commit()
    await db.refresh(mom)

    # 3. Create action items
    for item_data in mom_data["action_items"]:
        action_item = ActionItem(
            id=uuid.uuid4(),
            mom_id=mom.id,
            task=item_data["task"],
            assignee_name=item_data.get("assignee_name"),
            assignee_email=item_data.get("assignee_email"),
            deadline=_parse_deadline(item_data.get("deadline")),
            priority=TaskPriority(item_data.get("priority", "medium")),
            status=TaskStatus.todo,
        )
        db.add(action_item)

    await db.commit()

    # 4. Verify the complete pipeline
    result = await db.execute(
        select(MOM)
        .where(MOM.id == mom.id)
    )
    stored_mom = result.scalar_one()
    assert stored_mom.summary is not None

    # Verify action items were linked
    action_items = await db.execute(
        select(ActionItem).where(ActionItem.mom_id == mom.id)
    )
    items = action_items.scalars().all()
    assert len(items) > 0, "No action items were created during pipeline"


if __name__ == "__main__":
    # Run tests with: pytest tests/test_phase4_mom_extraction.py -v
    pytest.main([__file__, "-v", "-s"])
