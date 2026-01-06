from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.exception_handlers import domain_exception_handler
from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.check_ins import router as check_ins_router
from app.api.routers.freezes import router as freezes_router
from app.api.routers.habits import router as habits_router
from app.api.routers.users import router as users_router
from app.core.config import settings
from app.core.exceptions import DomainException

app = FastAPI(title=settings.app_name)
app.add_exception_handler(DomainException, domain_exception_handler)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(habits_router)
app.include_router(check_ins_router)
app.include_router(freezes_router)
app.include_router(analytics_router)


@app.get("/health", response_model=None)
async def health(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str] | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Database unavailable"},
        )
    return {"status": "ok"}
