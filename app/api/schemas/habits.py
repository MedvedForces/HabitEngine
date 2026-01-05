from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HabitBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    habit_type: str
    schedule_type: str
    target_value: Decimal | None = None
    unit: str | None = None
    weekdays: list[int] | None = None
    weekly_target: int | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.habit_type not in {"boolean", "quantitative"}:
            raise ValueError("Invalid habit type")
        if self.schedule_type not in {"daily", "weekdays", "weekly_quota"}:
            raise ValueError("Invalid schedule type")

        if self.habit_type == "boolean":
            if self.target_value is not None or self.unit is not None:
                raise ValueError("Boolean habits cannot have target_value or unit")
        else:
            if self.target_value is None or self.target_value <= 0:
                raise ValueError("Quantitative target_value must be positive")
            if not self.unit or not self.unit.strip():
                raise ValueError("Quantitative unit is required")
            self.unit = self.unit.strip()

        if self.schedule_type == "daily":
            if self.weekdays or self.weekly_target is not None:
                raise ValueError("Daily schedule cannot use weekdays or weekly_target")
        elif self.schedule_type == "weekdays":
            if not self.weekdays:
                raise ValueError("weekdays is required")
            if len(set(self.weekdays)) != len(self.weekdays):
                raise ValueError("weekdays must be unique")
            if any(day not in range(1, 8) for day in self.weekdays):
                raise ValueError("weekdays must contain ISO values 1..7")
            if self.weekly_target is not None:
                raise ValueError("weekdays schedule cannot use weekly_target")
        else:
            if self.weekdays:
                raise ValueError("weekly_quota cannot use weekdays")
            if self.weekly_target not in range(1, 8):
                raise ValueError("weekly_target must be between 1 and 7")

        return self


class CreateHabitRequest(HabitBase):
    pass


class UpdateHabitRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    habit_type: str | None = None
    schedule_type: str | None = None
    target_value: Decimal | None = None
    unit: str | None = None
    weekdays: list[int] | None = None
    weekly_target: int | None = None


class HabitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    habit_type: str
    schedule_type: str
    target_value: Decimal | None
    unit: str | None
    weekdays: list[int] = []
    weekly_target: int | None
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
