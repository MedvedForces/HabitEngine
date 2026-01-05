from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository

password_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def hash_password(password: str) -> str:
    import asyncio

    return await asyncio.to_thread(password_hasher.hash, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    import asyncio

    def verify() -> bool:
        try:
            password_hasher.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            return False

    return await asyncio.to_thread(verify)


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_user_id_from_token(token: str) -> UUID:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        return UUID(subject)
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise credentials_exception from None


async def get_current_user(
    token: str,
    session: AsyncSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = await get_user_id_from_token(token)
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user
