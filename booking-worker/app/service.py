from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus
from app.schemas import BookingRequested


def persist_booking(
    db: Session,
    booking_request: BookingRequested,
    status: BookingStatus,
    total_price: float,
) -> Booking:
    booking = Booking(
        user_id=booking_request.user_id,
        event_id=booking_request.event_id,
        tickets=booking_request.tickets,
        total_price=total_price,
        status=status,
    )
    with db.begin():
        db.add(booking)
    db.refresh(booking)
    return booking


def booking_event_payload(
    booking: Booking,
    booking_request: BookingRequested,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "booking_id": booking.id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "tickets": booking.tickets,
        "status": booking.status.value,
        "total_price": booking.total_price,
        "requested_at": booking_request.requested_at.isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    if reason is not None:
        payload["reason"] = reason
    return payload
