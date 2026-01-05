from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.habits import CreateHabitRequest, UpdateHabitRequest
from app.core.exceptions import ConflictException, NotFoundException
from app.models.habit import Habit
from app.repositories.habit_repository import HabitRepository


class HabitService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.repository = HabitRepository(session)

    async def create(self, payload: CreateHabitRequest) -> Habit:
        habit = Habit(
            user_id=self.user_id,
            name=payload.name,
            habit_type=payload.habit_type,
            schedule_type=payload.schedule_type,
            target_value=payload.target_value,
            unit=payload.unit,
            weekly_target=payload.weekly_target,
        )
        await self.repository.add(habit)
        await self.repository.replace_weekdays(habit, payload.weekdays or [])
        await self.session.commit()
        await self.session.refresh(habit)
        return await self.repository.get_by_id(habit.id, self.user_id)

    async def get_all(self, include_archived: bool) -> list[Habit]:
        return await self.repository.get_all(self.user_id, include_archived)

    async def get(self, habit_id: UUID) -> Habit:
        habit = await self.repository.get_by_id(habit_id, self.user_id)
        if habit is None:
            raise NotFoundException("Habit not found")
        return habit

    async def update(self, habit_id: UUID, payload: UpdateHabitRequest) -> Habit:
        habit = await self.get(habit_id)
        data = payload.model_dump(exclude_unset=True)
        for field in (
            "name",
            "habit_type",
            "schedule_type",
            "target_value",
            "unit",
            "weekly_target",
        ):
            if field in data:
                setattr(habit, field, data[field])
        if "weekdays" in data:
            weekdays = data["weekdays"]
        else:
            weekdays = [entry.weekday for entry in habit.weekdays]

        result = CreateHabitRequest(
            name=habit.name,
            habit_type=habit.habit_type,
            schedule_type=habit.schedule_type,
            target_value=habit.target_value,
            unit=habit.unit,
            weekdays=weekdays,
            weekly_target=habit.weekly_target,
        )
        await self.repository.replace_weekdays(habit, result.weekdays or [])
        await self.session.commit()
        await self.session.refresh(habit)
        return await self.repository.get_by_id(habit.id, self.user_id)

    async def archive(self, habit_id: UUID) -> Habit:
        habit = await self.get(habit_id)
        if habit.is_archived:
            raise ConflictException("Habit is already archived")
        habit.is_archived = True
        habit.archived_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(habit)
        return habit

    async def restore(self, habit_id: UUID) -> Habit:
        habit = await self.get(habit_id)
        if not habit.is_archived:
            raise ConflictException("Habit is already active")
        habit.is_archived = False
        habit.archived_at = None
        await self.session.commit()
        await self.session.refresh(habit)
        return habit
