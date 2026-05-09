from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Booking
from app.rabbitmq import RabbitMQProducer, producer
from app.schemas import (
    BookingAcceptedResponse,
    BookingMessage,
    BookingRequest,
    BookingResponse,
)
from app.services.event_client import EventClient, event_client


router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_event_client() -> EventClient:
    return event_client


def get_rabbitmq_producer() -> RabbitMQProducer:
    return producer


@router.get("/users/{user_id}", response_model=list[BookingResponse])
def list_user_bookings(
    user_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> list[Booking]:
    return list(
        db.execute(
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        ).scalars()
    )


@router.post(
    "",
    response_model=BookingAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_booking(
    booking_in: BookingRequest,
    events: EventClient = Depends(get_event_client),
    queue: RabbitMQProducer = Depends(get_rabbitmq_producer),
) -> BookingAcceptedResponse:
    await events.ensure_reachable()

    booking_message = BookingMessage(
        user_id=booking_in.user_id,
        event_id=booking_in.event_id,
        tickets=booking_in.tickets,
        requested_at=datetime.now(timezone.utc),
    )
    await queue.publish_booking(booking_message)

    return BookingAcceptedResponse(message="Booking request accepted for processing")
