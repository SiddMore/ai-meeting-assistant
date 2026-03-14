import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.mom import MOM
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.db.models.action_item import ActionItem


@pytest.mark.asyncio
async def test_semantic_search_basic(db: AsyncSession):
    """Test basic semantic search functionality."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create test MOMs with different content
    mom1 = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Discuss project timeline and deliverables",
        key_decisions="Approved Q2 timeline",
        full_content="We discussed the project timeline and agreed on deliverables for Q2. The team will focus on backend development first.",
        content_vector=[0.1] * 1536,  # Dummy vector
        created_at=datetime.utcnow()
    )

    mom2 = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Marketing strategy session",
        key_decisions="Launch social media campaign",
        full_content="The marketing team discussed social media strategy and decided to launch a campaign on Instagram and Twitter.",
        content_vector=[0.2] * 1536,  # Dummy vector
        created_at=datetime.utcnow()
    )

    await db.add(mom1)
    await db.add(mom2)
    await db.commit()

    # Test search endpoint
    response = await client.get("/api/moms/search?q=timeline")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 1
    assert results[0]["id"] == str(mom1.id)


@pytest.mark.asyncio
async def test_semantic_search_multiple_results(db: AsyncSession):
    """Test search returning multiple relevant results."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create test MOMs with similar content
    mom1 = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Discuss project timeline",
        key_decisions="Approved Q2 timeline",
        full_content="We discussed the project timeline and agreed on deliverables for Q2. The team will focus on backend development first.",
        content_vector=[0.1] * 1536,
        created_at=datetime.utcnow()
    )

    mom2 = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Timeline review meeting",
        key_decisions="Extended deadline by 2 weeks",
        full_content="Reviewed project timeline and decided to extend the deadline by two weeks to accommodate additional features.",
        content_vector=[0.15] * 1536,
        created_at=datetime.utcnow()
    )

    mom3 = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Budget planning",
        key_decisions="Allocated Q3 budget",
        full_content="Discussed budget allocation for Q3 projects and marketing initiatives.",
        content_vector=[0.3] * 1536,
        created_at=datetime.utcnow()
    )

    await db.add(mom1)
    await db.add(mom2)
    await db.add(mom3)
    await db.commit()

    # Test search for "timeline" should return both timeline-related MOMs
    response = await client.get("/api/moms/search?q=timeline")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 2
    result_ids = {result["id"] for result in results}
    assert str(mom1.id) in result_ids
    assert str(mom2.id) in result_ids


@pytest.mark.asyncio
async def test_semantic_search_no_results(db: AsyncSession):
    """Test search with no matching results."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create test MOMs
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Discuss project timeline",
        key_decisions="Approved Q2 timeline",
        full_content="We discussed the project timeline and agreed on deliverables for Q2.",
        content_vector=[0.1] * 1536,
        created_at=datetime.utcnow()
    )

    await db.add(mom)
    await db.commit()

    # Test search for unrelated term
    response = await client.get("/api/moms/search?q=unrelated")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_semantic_search_empty_query(db: AsyncSession):
    """Test search with empty query."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create test MOMs
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Discuss project timeline",
        key_decisions="Approved Q2 timeline",
        full_content="We discussed the project timeline and agreed on deliverables for Q2.",
        content_vector=[0.1] * 1536,
        created_at=datetime.utcnow()
    )

    await db.add(mom)
    await db.commit()

    # Test search with empty query
    response = await client.get("/api/moms/search?q=")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 1


@pytest.mark.asyncio
async def test_semantic_search_pagination(db: AsyncSession):
    """Test search pagination."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create multiple MOMs
    moms = []
    for i in range(10):
        mom = MOM(
            id=uuid.uuid4(),
            meeting_id=meeting.id,
            summary=f"Meeting {i+1} summary",
            key_decisions=f"Decision {i+1}",
            full_content=f"Content for meeting {i+1}",
            content_vector=[0.1 * (i+1)] * 1536,
            created_at=datetime.utcnow()
        )
        moms.append(mom)
        await db.add(mom)
    await db.commit()

    # Test search with pagination
    response = await client.get("/api/moms/search?q=meeting&limit=5")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 5

    # Test search with offset
    response = await client.get("/api/moms/search?q=meeting&limit=5&offset=5")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 5


@pytest.mark.asyncio
async def test_semantic_search_with_action_items(db: AsyncSession):
    """Test search with action items included."""
    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        provider="local",
        provider_id="test123"
    )
    await db.add(user)
    await db.commit()

    # Create test meeting
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Project Kickoff",
        platform="Zoom",
        meeting_url="https://zoom.us/test",
        user_id=user.id,
        created_at=datetime.utcnow()
    )
    await db.add(meeting)
    await db.commit()

    # Create test MOM with action items
    mom = MOM(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        summary="Discuss project timeline",
        key_decisions="Approved Q2 timeline",
        full_content="We discussed the project timeline and agreed on deliverables for Q2. The team will focus on backend development first.",
        content_vector=[0.1] * 1536,
        created_at=datetime.utcnow()
    )

    action_item = ActionItem(
        id=uuid.uuid4(),
        task="Complete backend development",
        assignee_name="John Doe",
        assignee_email="john@example.com",
        deadline="2024-05-15",
        status="todo",
        priority="high",
        mom_id=mom.id,
        created_at=datetime.utcnow()
    )

    await db.add(mom)
    await db.add(action_item)
    await db.commit()

    # Test search
    response = await client.get("/api/moms/search?q=backend")
    assert response.status_code == 200
    results = await response.json()
    assert len(results) == 1
    assert results[0]["id"] == str(mom.id)
    assert len(results[0]["action_items"]) == 1