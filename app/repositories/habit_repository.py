from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.habit import Habit, HabitWeekday


class HabitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, habit_id: UUID, user_id: UUID) -> Habit | None:
        result = await self.session.execute(
            select(Habit)
            .where(Habit.id == habit_id, Habit.user_id == user_id)
            .options(selectinload(Habit.weekdays))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: UUID,
        include_archived: bool,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .where(Habit.user_id == user_id)
            .options(selectinload(Habit.weekdays))
            .order_by(Habit.created_at)
        )
        if not include_archived:
            statement = statement.where(Habit.is_archived.is_(False))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add(self, habit: Habit) -> Habit:
        self.session.add(habit)
        await self.session.flush()
        return habit

    async def replace_weekdays(self, habit: Habit, weekdays: list[int]) -> None:
        await self.session.execute(delete(HabitWeekday).where(HabitWeekday.habit_id == habit.id))
        for weekday in weekdays:
            self.session.add(HabitWeekday(habit_id=habit.id, weekday=weekday))
