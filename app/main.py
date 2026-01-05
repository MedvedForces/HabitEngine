from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.exception_handlers import domain_exception_handler
from app.core.config import settings
from app.core.exceptions import DomainException

app = FastAPI(title=settings.app_name)
app.add_exception_handler(DomainException, domain_exception_handler)


@app.get("/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
