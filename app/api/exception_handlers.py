from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConflictException,
    DomainException,
    NotFoundException,
    ValidationDomainException,
)


async def domain_exception_handler(
    request: Request,
    exc: DomainException,
) -> JSONResponse:
    status_codes = {
        NotFoundException: 404,
        ConflictException: 409,
        ValidationDomainException: 422,
    }
    status_code = status_codes.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})
