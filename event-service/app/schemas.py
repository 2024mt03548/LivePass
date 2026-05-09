from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import EventStatus


class EventBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    venue: str = Field(..., min_length=1, max_length=255)
    event_date: datetime
    price: float = Field(..., ge=0)
    available_seats: int = Field(..., ge=0)
    status: EventStatus = EventStatus.ACTIVE


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    venue: str | None = Field(default=None, min_length=1, max_length=255)
    event_date: datetime | None = None
    price: float | None = Field(default=None, ge=0)
    available_seats: int | None = Field(default=None, ge=0)
    status: EventStatus | None = None


class EventResponse(EventBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryReserveRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    tickets: int = Field(..., gt=0)


class InventoryReserveResponse(BaseModel):
    success: bool
    reason: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
