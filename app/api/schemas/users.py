from datetime import datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class UpdateUserRequest(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        timezone = value.strip()
        if timezone not in available_timezones():
            raise ValueError("Invalid IANA timezone")
        return timezone
