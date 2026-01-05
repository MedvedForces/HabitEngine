from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.check_ins import CreateCheckInRequest
from app.core.exceptions import ConflictException, NotFoundException, ValidationDomainException
from app.models.check_in import CheckIn
from app.repositories.check_in_repository import CheckInRepository


class CheckInService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.repository = CheckInRepository(session)

    async def create(
        self,
        habit_id: UUID,
        payload: CreateCheckInRequest,
        timezone: str,
    ) -> CheckIn:
        habit = await self.repository.lock_habit(habit_id, self.user_id)
        if habit is None:
            raise NotFoundException("Habit not found")
        if habit.is_archived:
            raise ConflictException("Archived habits cannot receive check-ins")

        logged_at = payload.logged_at or datetime.now(UTC)
        if logged_at.tzinfo is None:
            logged_at = logged_at.replace(tzinfo=UTC)
        logged_at = logged_at.astimezone(UTC)
        local_date = logged_at.astimezone(ZoneInfo(timezone)).date()

        if habit.habit_type == "boolean":
            value = Decimal("1") if payload.value is None else payload.value
            if value != Decimal("1"):
                raise ValidationDomainException("Boolean check-in value must be 1")
            if await self.repository.exists_on_date(habit_id, local_date):
                raise ConflictException("A check-in already exists for this local date")
        else:
            if payload.value is None or payload.value <= 0:
                raise ValidationDomainException("Quantitative check-in value must be positive")
            value = payload.value

        check_in = CheckIn(
            habit_id=habit.id,
            logged_at=logged_at,
            local_date=local_date,
            value=value,
        )
        await self.repository.add(check_in)
        await self.session.commit()
        await self.session.refresh(check_in)
        return check_in

    async def get_habit_or_404(self, habit_id: UUID):
        habit = await self.repository.lock_habit(habit_id, self.user_id)
        if habit is None:
            raise NotFoundException("Habit not found")
        return habit

    async def list(
        self,
        habit_id: UUID,
        date_from: date | None,
        date_to: date | None,
        limit: int,
        cursor: str | None,
    ):
        await self.get_habit_or_404(habit_id)
        return await self.repository.paginate(
            habit_id,
            date_from,
            date_to,
            limit,
            cursor,
        )

    async def get(self, habit_id: UUID, check_in_id: UUID) -> CheckIn:
        await self.get_habit_or_404(habit_id)
        check_in = await self.repository.get_by_id(check_in_id, habit_id)
        if check_in is None:
            raise NotFoundException("Check-in not found")
        return check_in

    async def delete(self, habit_id: UUID, check_in_id: UUID) -> None:
        await self.get_habit_or_404(habit_id)
        check_in = await self.repository.get_by_id(check_in_id, habit_id)
        if check_in is None:
            raise NotFoundException("Check-in not found")
        await self.session.delete(check_in)
        await self.session.commit()
