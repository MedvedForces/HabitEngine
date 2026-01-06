from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    unit: str


class HeatmapItem(BaseModel):
    date: date
    value: Decimal
    target_value: Decimal
    is_completed: bool
    is_frozen: bool
    intensity: int


class SummaryResponse(BaseModel):
    total_completed_days: int
    total_check_ins: int
    completion_rate_7d: float
    completion_rate_30d: float
