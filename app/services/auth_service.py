from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def register(self, email: str, password: str, timezone: str) -> User:
        if await self.repository.get_by_email(email):
            raise ConflictException("Email already registered")

        hashed_password = await hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            timezone=timezone,
        )
        await self.repository.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException("Email already registered") from exc
        await self.session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> str:
        user = await self.repository.get_by_email(email)
        if user is None:
            raise UnauthorizedException("Incorrect email or password")

        valid_password = await verify_password(password, user.hashed_password)
        if not valid_password:
            raise UnauthorizedException("Incorrect email or password")

        return create_access_token(user.id)
