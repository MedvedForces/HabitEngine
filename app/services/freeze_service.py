from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.freeze import HabitFreeze
from app.repositories.check_in_repository import CheckInRepository
from app.repositories.freezes_repository import FreezeRepository


class FreezeService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.check_ins = CheckInRepository(session)
        self.repository = FreezeRepository(session)

    async def create(
        self,
        habit_id: UUID,
        local_date: date | None,
        timezone: str,
    ) -> HabitFreeze:
        habit = await self.check_ins.lock_habit(habit_id, self.user_id)
        if habit is None:
            raise NotFoundException("Habit not found")
        if habit.is_archived:
            raise ConflictException("Archived habits cannot be frozen")

        freeze_date = local_date or datetime.now(UTC).astimezone(ZoneInfo(timezone)).date()
        if await self.repository.get(habit_id, freeze_date):
            raise ConflictException("This date is already frozen")

        freeze = HabitFreeze(habit_id=habit_id, local_date=freeze_date)
        await self.repository.add(freeze)
        await self.session.commit()
        await self.session.refresh(freeze)
        return freeze

    async def delete(self, habit_id: UUID, local_date: date) -> None:
        habit = await self.check_ins.lock_habit(habit_id, self.user_id)
        if habit is None:
            raise NotFoundException("Habit not found")
        freeze = await self.repository.get(habit_id, local_date)
        if freeze is None:
            raise NotFoundException("Freeze not found")
        await self.session.delete(freeze)
        await self.session.commit()
