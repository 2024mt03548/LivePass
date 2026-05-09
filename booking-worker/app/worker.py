import asyncio
import json
import logging
from typing import Any

from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.event_client import EventServiceClient
from app.models import BookingStatus
from app.rabbitmq import consumer
from app.schemas import BookingRequested
from app.service import booking_event_payload, persist_booking


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("booking-worker")
settings = get_settings()


event_service = EventServiceClient(
    base_url=settings.event_service_url,
    timeout_seconds=settings.event_service_timeout_seconds,
    retry_attempts=settings.event_service_retry_attempts,
    retry_backoff_seconds=settings.event_service_retry_backoff_seconds,
)


def decode_message(message: AbstractIncomingMessage) -> BookingRequested:
    payload: Any = json.loads(message.body.decode("utf-8"))
    return BookingRequested.model_validate(payload)


async def publish_outcome_event(routing_key: str, payload: dict[str, Any]) -> None:
    for attempt in range(1, settings.event_service_retry_attempts + 1):
        try:
            await consumer.publish_event(routing_key, payload)
            return
        except Exception as exc:
            logger.warning(
                "booking_outcome_publish_failed",
                extra={
                    "routing_key": routing_key,
                    "attempt": attempt,
                    "max_attempts": settings.event_service_retry_attempts,
                    "error": str(exc),
                },
            )
            if attempt == settings.event_service_retry_attempts:
                raise
            await asyncio.sleep(settings.event_service_retry_backoff_seconds * attempt)


async def handle_message(message: AbstractIncomingMessage) -> None:
    try:
        booking_request = decode_message(message)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        logger.warning("discarding_invalid_booking_request", extra={"error": str(exc)})
        await message.ack()
        return

    try:
        reservation = await event_service.reserve_inventory(
            event_id=booking_request.event_id,
            tickets=booking_request.tickets,
        )
    except Exception as exc:
        logger.exception(
            "reservation_unavailable",
            extra={
                "user_id": booking_request.user_id,
                "event_id": booking_request.event_id,
                "tickets": booking_request.tickets,
                "error": str(exc),
            },
        )
        await message.nack(requeue=True)
        return

    db = SessionLocal()
    try:
        if reservation.success:
            booking = persist_booking(
                db,
                booking_request,
                BookingStatus.CONFIRMED,
                reservation.total_price or 0.0,
            )
            routing_key = settings.booking_confirmed_queue
            outcome_payload = booking_event_payload(booking, booking_request)
            logger.info(
                "booking_confirmed",
                extra={
                    "booking_id": booking.id,
                    "user_id": booking.user_id,
                    "event_id": booking.event_id,
                    "tickets": booking.tickets,
                },
            )
        else:
            booking = persist_booking(
                db,
                booking_request,
                BookingStatus.FAILED,
                0.0,
            )
            routing_key = settings.booking_rejected_queue
            outcome_payload = booking_event_payload(
                booking,
                booking_request,
                reservation.reason,
            )
            logger.info(
                "booking_rejected",
                extra={
                    "booking_id": booking.id,
                    "user_id": booking.user_id,
                    "event_id": booking.event_id,
                    "tickets": booking.tickets,
                    "reason": reservation.reason,
                },
            )
    except Exception as exc:
        db.rollback()
        logger.exception("booking_persistence_failed", extra={"error": str(exc)})
        await message.nack(requeue=True)
        return
    finally:
        db.close()

    try:
        await publish_outcome_event(routing_key, outcome_payload)
    except Exception as exc:
        logger.exception(
            "booking_outcome_publish_exhausted",
            extra={
                "booking_id": outcome_payload["booking_id"],
                "routing_key": routing_key,
                "error": str(exc),
            },
        )

    await message.ack()


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    queue = await consumer.connect()
    await queue.consume(handle_message, no_ack=False)
    logger.info("consuming_queue", extra={"queue": settings.booking_queue})

    try:
        await asyncio.Future()
    finally:
        await consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
