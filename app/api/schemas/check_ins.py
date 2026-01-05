from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CreateCheckInRequest(BaseModel):
    value: Decimal | None = None
    logged_at: datetime | None = None

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime | None) -> datetime | None:
        return value


class CheckInResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    habit_id: UUID
    logged_at: datetime
    local_date: date
    value: Decimal
    created_at: datetime


class CheckInListResponse(BaseModel):
    items: list[CheckInResponse]
    next_cursor: str | None
