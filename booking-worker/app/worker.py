import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis
from aio_pika.abc import AbstractIncomingMessage
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Booking, BookingStatus, Event, EventStatus
from app.rabbitmq import consumer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("booking-worker")
settings = get_settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

EVENTS_LIST_CACHE_KEY = "events:list"
EVENT_DETAIL_CACHE_KEY = "event:{event_id}"


class BookingMessage(BaseModel):
    user_id: int = Field(..., gt=0)
    event_id: int = Field(..., gt=0)
    tickets: int = Field(..., gt=0)
    total_price: float = Field(..., ge=0)


class BookingProcessingError(Exception):
    pass


async def invalidate_event_cache(event_id: int) -> None:
    await redis_client.delete(
        EVENTS_LIST_CACHE_KEY,
        EVENT_DETAIL_CACHE_KEY.format(event_id=event_id),
    )


def decode_message(message: AbstractIncomingMessage) -> BookingMessage:
    payload: Any = json.loads(message.body.decode("utf-8"))
    return BookingMessage.model_validate(payload)


def process_booking_transaction(db: Session, booking_message: BookingMessage) -> None:
    with db.begin():
        statement = (
            select(Event)
            .where(Event.id == booking_message.event_id)
            .with_for_update()
        )
        event = db.execute(statement).scalar_one_or_none()

        if event is None:
            raise BookingProcessingError(
                f"Event {booking_message.event_id} does not exist"
            )

        if event.status != EventStatus.ACTIVE:
            raise BookingProcessingError(
                f"Event {booking_message.event_id} is not active"
            )

        if event.available_seats < booking_message.tickets:
            raise BookingProcessingError(
                f"Event {booking_message.event_id} does not have enough seats"
            )

        booking = Booking(
            user_id=booking_message.user_id,
            event_id=booking_message.event_id,
            tickets=booking_message.tickets,
            total_price=booking_message.total_price,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)
        event.available_seats -= booking_message.tickets

        if event.available_seats == 0:
            event.status = EventStatus.SOLD_OUT


async def handle_message(message: AbstractIncomingMessage) -> None:
    try:
        booking_message = decode_message(message)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        logger.warning("Discarding invalid booking message: %s", exc)
        await message.ack()
        return

    db = SessionLocal()
    try:
        process_booking_transaction(db, booking_message)
    except BookingProcessingError as exc:
        logger.warning("Booking rejected: %s", exc)
        await message.ack()
    except Exception:
        db.rollback()
        logger.exception("Unexpected booking processing failure")
        await message.nack(requeue=True)
    else:
        await invalidate_event_cache(booking_message.event_id)
        logger.info(
            "Booking confirmed for user_id=%s event_id=%s tickets=%s",
            booking_message.user_id,
            booking_message.event_id,
            booking_message.tickets,
        )
        await message.ack()
    finally:
        db.close()


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    queue = await consumer.connect()
    await queue.consume(handle_message, no_ack=False)
    logger.info("Consuming queue '%s'", settings.booking_queue)

    try:
        await asyncio.Future()
    finally:
        await consumer.close()
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
