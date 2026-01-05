import base64
import binascii
from datetime import date
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationDomainException
from app.models.check_in import CheckIn
from app.models.habit import Habit


class CheckInRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_habit(self, habit_id: UUID, user_id: UUID) -> Habit | None:
        result = await self.session.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def exists_on_date(self, habit_id: UUID, local_date: date) -> bool:
        result = await self.session.execute(
            select(CheckIn.id).where(
                CheckIn.habit_id == habit_id,
                CheckIn.local_date == local_date,
            )
        )
        return result.first() is not None

    async def add(self, check_in: CheckIn) -> CheckIn:
        self.session.add(check_in)
        await self.session.flush()
        return check_in

    async def get_by_id(
        self,
        check_in_id: UUID,
        habit_id: UUID,
    ) -> CheckIn | None:
        result = await self.session.execute(
            select(CheckIn).where(
                CheckIn.id == check_in_id,
                CheckIn.habit_id == habit_id,
            )
        )
        return result.scalar_one_or_none()

    async def paginate(
        self,
        habit_id: UUID,
        date_from: date | None,
        date_to: date | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[CheckIn], str | None]:
        statement = select(CheckIn).where(CheckIn.habit_id == habit_id)
        if date_from is not None:
            statement = statement.where(CheckIn.local_date >= date_from)
        if date_to is not None:
            statement = statement.where(CheckIn.local_date <= date_to)

        if cursor:
            cursor_date, cursor_id = decode_cursor(cursor)
            statement = statement.where(
                tuple_(CheckIn.local_date, CheckIn.id) < tuple_(cursor_date, cursor_id)
            )

        statement = statement.order_by(
            CheckIn.local_date.desc(),
            CheckIn.id.desc(),
        ).limit(limit + 1)
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1]) if has_next and items else None
        return items, next_cursor


def encode_cursor(check_in: CheckIn) -> str:
    raw = f"{check_in.local_date.isoformat()}|{check_in.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[date, UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + padding).decode()
        date_text, id_text = raw.split("|", 1)
        return date.fromisoformat(date_text), UUID(id_text)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise ValidationDomainException("Invalid cursor") from None
