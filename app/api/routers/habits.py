from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.api.schemas.habits import (
    CreateHabitRequest,
    HabitResponse,
    UpdateHabitRequest,
)
from app.models.user import User
from app.services.habit_service import HabitService

router = APIRouter(prefix="/habits", tags=["habits"])


def to_response(habit) -> HabitResponse:
    return HabitResponse(
        id=habit.id,
        name=habit.name,
        habit_type=habit.habit_type,
        schedule_type=habit.schedule_type,
        target_value=habit.target_value,
        unit=habit.unit,
        weekdays=sorted(entry.weekday for entry in habit.weekdays),
        weekly_target=habit.weekly_target,
        is_archived=habit.is_archived,
        archived_at=habit.archived_at,
        created_at=habit.created_at,
        updated_at=habit.updated_at,
    )


@router.post("", response_model=HabitResponse, status_code=201)
async def create_habit(
    payload: CreateHabitRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HabitResponse:
    habit = await HabitService(session, user.id).create(payload)
    return to_response(habit)


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    include_archived: bool = False,
    user: Annotated[User, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> list[HabitResponse]:
    habits = await HabitService(session, user.id).get_all(include_archived)
    return [to_response(habit) for habit in habits]


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HabitResponse:
    habit = await HabitService(session, user.id).get(habit_id)
    return to_response(habit)


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: UUID,
    payload: UpdateHabitRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HabitResponse:
    habit = await HabitService(session, user.id).update(habit_id, payload)
    return to_response(habit)


@router.post("/{habit_id}/archive", response_model=HabitResponse)
async def archive_habit(
    habit_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HabitResponse:
    habit = await HabitService(session, user.id).archive(habit_id)
    return to_response(habit)


@router.post("/{habit_id}/restore", response_model=HabitResponse)
async def restore_habit(
    habit_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HabitResponse:
    habit = await HabitService(session, user.id).restore(habit_id)
    return to_response(habit)
