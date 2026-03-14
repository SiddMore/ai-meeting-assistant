from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.db.models.mom import MOM
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.mom import MOMOut, MOMListItem

router = APIRouter()


@router.get("/", response_model=List[MOMListItem])
async def list_moms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all MOMs for the current user."""
    from app.db.models.meeting import Meeting
    result = await db.execute(
        select(MOM)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(Meeting.user_id == current_user.id)
        .order_by(MOM.created_at.desc())
    )
    moms = result.scalars().all()
    return [MOMListItem.from_orm(mom) for mom in moms]


@router.get("/{mom_id}", response_model=MOMOut)
async def get_mom(
    mom_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific MOM by ID."""
    from uuid import UUID
    from app.db.models.meeting import Meeting
    mom_uuid = UUID(mom_id)

    result = await db.execute(
        select(MOM)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(MOM.id == mom_uuid, Meeting.user_id == current_user.id)
    )
    mom = result.scalar_one_or_none()

    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found")

    return MOMOut.from_orm(mom)


@router.post("/{mom_id}/send-email")
async def send_mom_email(
    mom_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send MOM via email to meeting participants (Phase 6)."""
    from uuid import UUID
    from app.db.models.meeting import Meeting
    mom_uuid = UUID(mom_id)

    result = await db.execute(
        select(MOM)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(MOM.id == mom_uuid, Meeting.user_id == current_user.id)
    )
    mom = result.scalar_one_or_none()

    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found")

    # Enqueue real email task (Phase 6)
    from app.workers.email import send_mom_email_task
    send_mom_email_task.delay(str(mom.id))

    return {"status": "queued", "mom_id": str(mom.id)}


@router.get("/search/", response_model=List[MOMListItem])
async def search_moms(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic search through MOMs."""
    # TODO: Implement semantic search with pgvector
    return []
