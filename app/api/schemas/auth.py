from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator


def normalize_timezone(value: str) -> str:
    timezone = value.strip()
    if timezone not in available_timezones():
        raise ValueError("Invalid IANA timezone")
    return timezone


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8)
    timezone: str = "UTC"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return normalize_timezone(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
