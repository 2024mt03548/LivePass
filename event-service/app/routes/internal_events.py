from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event
from app.routes.events import invalidate_event_cache
from app.schemas import EventCreate, EventResponse, EventUpdate


router = APIRouter(prefix="/internal/events", tags=["internal-events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event_in: EventCreate, db: Session = Depends(get_db)) -> Event:
    event = Event(**event_in.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)

    await invalidate_event_cache(event.id)
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    await invalidate_event_cache(event.id)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, db: Session = Depends(get_db)) -> Response:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    db.delete(event)
    db.commit()

    await invalidate_event_cache(event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
