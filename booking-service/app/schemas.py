from datetime import datetime

from pydantic import BaseModel, Field


class BookingRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    event_id: int = Field(..., gt=0)
    tickets: int = Field(..., gt=0)


class BookingAcceptedResponse(BaseModel):
    message: str


class EventResponse(BaseModel):
    id: int
    name: str
    venue: str
    event_date: datetime
    price: float
    available_seats: int
    status: str
    created_at: datetime


class BookingMessage(BaseModel):
    user_id: int
    event_id: int
    tickets: int
    total_price: float
