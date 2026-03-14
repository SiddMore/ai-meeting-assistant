from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from uuid import UUID
from app.db.session import get_db
from app.db.models.action_item import ActionItem, TaskStatus, TaskPriority
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.mom import ActionItemOut

router = APIRouter()


@router.get("/", response_model=List[ActionItemOut])
async def list_action_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all action items for the current user."""
    from app.db.models.mom import MOM
    from app.db.models.meeting import Meeting
    result = await db.execute(
        select(ActionItem)
        .join(MOM, ActionItem.mom_id == MOM.id)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(Meeting.user_id == current_user.id)
        .order_by(ActionItem.created_at.desc())
    )
    items = result.scalars().all()
    return [ActionItemOut.from_orm(item) for item in items]


@router.patch("/{task_id}")
async def update_action_item(
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update action item status and/or priority."""
    from app.db.models.mom import MOM
    from app.db.models.meeting import Meeting
    task_uuid = UUID(task_id)

    # Verify ownership
    result = await db.execute(
        select(ActionItem)
        .join(MOM, ActionItem.mom_id == MOM.id)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(ActionItem.id == task_uuid, Meeting.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Update fields
    update_data = {}
    if status:
        try:
            update_data["status"] = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if priority:
        try:
            update_data["priority"] = TaskPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

    if update_data:
        await db.execute(
            update(ActionItem)
            .where(ActionItem.id == task_uuid)
            .values(**update_data)
        )
        await db.commit()

        # Enqueue calendar update if an event exists
        try:
            from app.workers.calendar_sync import update_action_item_calendar_event

            update_action_item_calendar_event.delay(str(task_uuid))
        except Exception:
            # Calendar sync failures should not break the main API flow
            pass

    return {"status": "updated", "task_id": task_id}


@router.delete("/{task_id}")
async def delete_action_item(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an action item."""
    from sqlalchemy import delete
    from app.db.models.mom import MOM
    from app.db.models.meeting import Meeting
    task_uuid = UUID(task_id)

    # Verify ownership and delete
    result = await db.execute(
        select(ActionItem)
        .join(MOM, ActionItem.mom_id == MOM.id)
        .join(Meeting, MOM.meeting_id == Meeting.id)
        .where(ActionItem.id == task_uuid, Meeting.user_id == current_user.id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    await db.execute(delete(ActionItem).where(ActionItem.id == task_uuid))
    await db.commit()

    # Enqueue calendar delete (best effort)
    try:
        from app.workers.calendar_sync import delete_action_item_calendar_event

        delete_action_item_calendar_event.delay(str(task_uuid))
    except Exception:
        pass

    return {"status": "deleted", "task_id": task_id}
