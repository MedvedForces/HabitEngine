from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.api.schemas.check_ins import (
    CheckInListResponse,
    CheckInResponse,
    CreateCheckInRequest,
)
from app.models.user import User
from app.services.check_in_service import CheckInService

router = APIRouter(prefix="/habits/{habit_id}", tags=["check-ins"])


@router.post("/check-ins", response_model=CheckInResponse, status_code=201)
async def create_check_in(
    habit_id: UUID,
    payload: CreateCheckInRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CheckInResponse:
    check_in = await CheckInService(session, user.id).create(
        habit_id,
        payload,
        user.timezone,
    )
    return CheckInResponse.model_validate(check_in)


@router.get("/check-ins", response_model=CheckInListResponse)
async def list_check_ins(
    habit_id: UUID,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    user: Annotated[User, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> CheckInListResponse:
    items, next_cursor = await CheckInService(session, user.id).list(
        habit_id,
        date_from,
        date_to,
        limit,
        cursor,
    )
    return CheckInListResponse(
        items=[CheckInResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


@router.get("/check-ins/{check_in_id}", response_model=CheckInResponse)
async def get_check_in(
    habit_id: UUID,
    check_in_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CheckInResponse:
    check_in = await CheckInService(session, user.id).get(habit_id, check_in_id)
    return CheckInResponse.model_validate(check_in)


@router.delete("/check-ins/{check_in_id}", status_code=204)
async def delete_check_in(
    habit_id: UUID,
    check_in_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await CheckInService(session, user.id).delete(habit_id, check_in_id)
    return Response(status_code=204)
