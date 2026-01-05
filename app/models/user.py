import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.habit import Habit


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    habits: Mapped[list["Habit"]] = relationship(back_populates="user")

    __table_args__ = (
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_empty"),
        CheckConstraint(
            "length(trim(timezone)) > 0",
            name="ck_users_timezone_not_empty",
        ),
    )
