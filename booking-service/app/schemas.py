from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    event_id: int = Field(..., gt=0)
    tickets: int = Field(..., gt=0)


class BookingAcceptedResponse(BaseModel):
    message: str


class BookingMessage(BaseModel):
    user_id: int
    event_id: int
    tickets: int
    requested_at: datetime

    model_config = ConfigDict(from_attributes=True)
