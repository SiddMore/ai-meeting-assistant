from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict
from uuid import UUID
from app.db.session import get_db
from app.db.models.meeting import Meeting
from app.db.models.mom import MOM
from app.db.models.action_item import ActionItem
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/stats", response_model=Dict[str, int])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for the current user."""
    
    # Count total meetings
    meetings_count = await db.execute(
        select(func.count()).select_from(Meeting).where(Meeting.user_id == current_user.id)
    )
    total_meetings = meetings_count.scalar_one_or_none() or 0
    
    # Count total MOMs
    moms_count = await db.execute(
        select(func.count()).select_from(MOM).join(Meeting, MOM.meeting_id == Meeting.id)
        .where(Meeting.user_id == current_user.id)
    )
    total_moms = moms_count.scalar_one_or_none() or 0
    
    # Count completed tasks
    completed_tasks_count = await db.execute(
        select(func.count()).select_from(ActionItem)
        .join(MOM, ActionItem.mom_id == MOM.id)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(Meeting.user_id == current_user.id, ActionItem.status == "completed")
    )
    completed_tasks = completed_tasks_count.scalar_one_or_none() or 0
    
    return {
        "total_meetings": total_meetings,
        "total_moms": total_moms,
        "completed_tasks": completed_tasks,
    }