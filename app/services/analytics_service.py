from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationDomainException
from app.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    def __init__(self, session: AsyncSession, user) -> None:
        self.session = session
        self.user = user
        self.repository = AnalyticsRepository(session)

    async def _owned_habit(self, habit_id: UUID):
        habit = await self.repository.get_owned_habit(habit_id, self.user.id)
        if habit is None:
            raise NotFoundException("Habit not found")
        return habit

    def today(self):
        return datetime.now(ZoneInfo(self.user.timezone)).date()

    async def streak(self, habit_id: UUID) -> dict:
        habit = await self._owned_habit(habit_id)
        today = self.today()
        result = await self.repository.get_streak(
            habit_id,
            self.user.id,
            today,
            habit["schedule_type"],
        )
        unit = "weeks" if habit["schedule_type"] == "weekly_quota" else "days"
        return {
            "current_streak": result["current_streak"],
            "longest_streak": result["longest_streak"],
            "unit": unit,
        }

    async def heatmap(self, habit_id: UUID, date_from, date_to) -> list[dict]:
        await self._owned_habit(habit_id)
        if date_from > date_to:
            raise ValidationDomainException("date_from must be before or equal to date_to")
        if (date_to - date_from).days > 365:
            raise ValidationDomainException("Heatmap range cannot exceed 366 days")
        return await self.repository.get_heatmap(
            habit_id,
            self.user.id,
            date_from,
            date_to,
        )

    async def summary(self, habit_id: UUID) -> dict:
        await self._owned_habit(habit_id)
        return await self.repository.get_summary(
            habit_id,
            self.user.id,
            self.today(),
        )
