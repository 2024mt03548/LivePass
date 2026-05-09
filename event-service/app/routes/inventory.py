import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event, EventStatus
from app.routes.events import invalidate_event_cache
from app.schemas import InventoryReserveRequest, InventoryReserveResponse


router = APIRouter(prefix="/internal/inventory", tags=["internal-inventory"])
logger = logging.getLogger("event-service.inventory")


@router.post("/reserve", response_model=InventoryReserveResponse)
async def reserve_inventory(
    reservation: InventoryReserveRequest,
    db: Session = Depends(get_db),
) -> InventoryReserveResponse:
    event = db.execute(
        select(Event)
        .where(Event.id == reservation.event_id)
        .with_for_update()
    ).scalar_one_or_none()

    if event is None:
        db.rollback()
        return InventoryReserveResponse(success=False, reason="event_not_found")

    if event.status != EventStatus.ACTIVE:
        db.rollback()
        return InventoryReserveResponse(success=False, reason="event_not_active")

    if event.available_seats < reservation.tickets:
        db.rollback()
        return InventoryReserveResponse(success=False, reason="insufficient_seats")

    unit_price = event.price
    total_price = unit_price * reservation.tickets

    event.available_seats -= reservation.tickets
    if event.available_seats == 0:
        event.status = EventStatus.SOLD_OUT

    db.commit()

    try:
        await invalidate_event_cache(event.id)
    except Exception:
        logger.exception(
            "inventory_cache_invalidation_failed",
            extra={"event_id": event.id},
        )

    return InventoryReserveResponse(
        success=True,
        unit_price=unit_price,
        total_price=total_price,
    )
