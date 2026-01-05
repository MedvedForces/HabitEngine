from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freeze import HabitFreeze


class FreezeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        habit_id: UUID,
        local_date: date,
    ) -> HabitFreeze | None:
        result = await self.session.execute(
            select(HabitFreeze).where(
                HabitFreeze.habit_id == habit_id,
                HabitFreeze.local_date == local_date,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, freeze: HabitFreeze) -> HabitFreeze:
        self.session.add(freeze)
        await self.session.flush()
        return freeze
