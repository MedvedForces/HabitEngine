from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_timezone(self, user: User, timezone: str) -> User:
        user.timezone = timezone
        await self.session.commit()
        await self.session.refresh(user)
        return user
