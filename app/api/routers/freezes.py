from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.api.schemas.freezes import CreateFreezeRequest
from app.models.user import User
from app.services.freeze_service import FreezeService

router = APIRouter(prefix="/habits/{habit_id}", tags=["freezes"])


@router.post("/freezes", status_code=201)
async def create_freeze(
    habit_id: UUID,
    payload: CreateFreezeRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    freeze = await FreezeService(session, user.id).create(
        habit_id,
        payload.local_date,
        user.timezone,
    )
    return {"habit_id": str(freeze.habit_id), "local_date": freeze.local_date}


@router.delete("/freezes/{local_date}", status_code=204)
async def delete_freeze(
    habit_id: UUID,
    local_date: date,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await FreezeService(session, user.id).delete(habit_id, local_date)
    return Response(status_code=204)
