from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Habit Tracker"
    environment: str = "local"
    database_url: str = (
        "postgresql+asyncpg://habit_user:habit_password@localhost:5432/habit_tracker"
    )
    jwt_secret: str = "change-me-in-production-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


settings = Settings()
