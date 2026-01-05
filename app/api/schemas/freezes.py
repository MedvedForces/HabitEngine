from datetime import date

from pydantic import BaseModel


class CreateFreezeRequest(BaseModel):
    local_date: date | None = None
