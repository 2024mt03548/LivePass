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
