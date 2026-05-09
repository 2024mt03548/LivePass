from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status

from app.rabbitmq import RabbitMQProducer, producer
from app.schemas import BookingAcceptedResponse, BookingMessage, BookingRequest
from app.services.event_client import EventClient, event_client


router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_event_client() -> EventClient:
    return event_client


def get_rabbitmq_producer() -> RabbitMQProducer:
    return producer


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
