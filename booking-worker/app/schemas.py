from datetime import datetime

from pydantic import BaseModel, Field


class BookingRequested(BaseModel):
    user_id: int = Field(..., gt=0)
    event_id: int = Field(..., gt=0)
    tickets: int = Field(..., gt=0)
    requested_at: datetime


class InventoryReservation(BaseModel):
    success: bool
    reason: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
