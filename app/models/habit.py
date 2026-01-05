import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Habit(Base, TimestampMixin):
    __tablename__ = "habits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    habit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weekly_target: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="habits")
    weekdays: Mapped[list["HabitWeekday"]] = relationship(
        back_populates="habit",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_habits_name_not_empty"),
        CheckConstraint(
            "habit_type IN ('boolean', 'quantitative')",
            name="ck_habits_habit_type",
        ),
        CheckConstraint(
            "schedule_type IN ('daily', 'weekdays', 'weekly_quota')",
            name="ck_habits_schedule_type",
        ),
        CheckConstraint(
            "(is_archived = false AND archived_at IS NULL)"
            " OR (is_archived = true AND archived_at IS NOT NULL)",
            name="ck_habits_archive_state",
        ),
        CheckConstraint(
            "weekly_target IS NULL OR weekly_target BETWEEN 1 AND 7",
            name="ck_habits_weekly_target",
        ),
        CheckConstraint(
            "(habit_type = 'boolean' AND target_value IS NULL AND unit IS NULL)"
            " OR (habit_type = 'quantitative'"
            " AND target_value > 0 AND unit IS NOT NULL)",
            name="ck_habits_type_fields",
        ),
        CheckConstraint(
            "(schedule_type = 'weekly_quota'"
            " AND weekly_target BETWEEN 1 AND 7)"
            " OR (schedule_type != 'weekly_quota' AND weekly_target IS NULL)",
            name="ck_habits_schedule_fields",
        ),
        Index(
            "ix_habits_user_archived_created",
            "user_id",
            "is_archived",
            "created_at",
        ),
    )


class HabitWeekday(Base):
    __tablename__ = "habit_weekdays"

    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    habit: Mapped["Habit"] = relationship(back_populates="weekdays")

    __table_args__ = (
        CheckConstraint(
            "weekday BETWEEN 1 AND 7",
            name="ck_habit_weekdays_weekday",
        ),
    )
