from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.api.schemas.users import UpdateUserRequest, UserResponse
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UpdateUserRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    updated_user = await UserService(session).update_timezone(
        user,
        payload.timezone,
    )
    return UserResponse.model_validate(updated_user)
