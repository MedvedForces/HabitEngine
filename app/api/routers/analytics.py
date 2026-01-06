from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.api.schemas.analytics import (
    HeatmapItem,
    StreakResponse,
    SummaryResponse,
)
from app.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/habits/{habit_id}/analytics", tags=["analytics"])


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    habit_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StreakResponse:
    result = await AnalyticsService(session, user).streak(habit_id)
    return StreakResponse.model_validate(result)


@router.get("/heatmap", response_model=list[HeatmapItem])
async def get_heatmap(
    habit_id: UUID,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[HeatmapItem]:
    result = await AnalyticsService(session, user).heatmap(
        habit_id,
        date_from,
        date_to,
    )
    return [HeatmapItem.model_validate(row) for row in result]


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    habit_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SummaryResponse:
    result = await AnalyticsService(session, user).summary(habit_id)
    return SummaryResponse.model_validate(result)
