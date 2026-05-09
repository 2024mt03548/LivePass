import json

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Event
from app.schemas import EventResponse


router = APIRouter(prefix="/events", tags=["events"])
settings = get_settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

EVENTS_LIST_CACHE_KEY = "events:list"
EVENT_DETAIL_CACHE_KEY = "event:{event_id}"
CACHE_TTL_SECONDS = 60


def serialize_event(event: Event) -> dict:
    return EventResponse.model_validate(event).model_dump(mode="json")


async def invalidate_event_cache(event_id: int | None = None) -> None:
    keys = [EVENTS_LIST_CACHE_KEY]
    if event_id is not None:
        keys.append(EVENT_DETAIL_CACHE_KEY.format(event_id=event_id))
    await redis_client.delete(*keys)


@router.get("", response_model=list[EventResponse])
async def list_events(db: Session = Depends(get_db)) -> list[dict]:
    cached_events = await redis_client.get(EVENTS_LIST_CACHE_KEY)
    if cached_events:
        print(f"returning from cache")
        return json.loads(cached_events)

    events = db.query(Event).order_by(Event.event_date.asc()).all()
    payload = [serialize_event(event) for event in events]
    await redis_client.setex(EVENTS_LIST_CACHE_KEY, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)) -> dict:
    cache_key = EVENT_DETAIL_CACHE_KEY.format(event_id=event_id)
    cached_event = await redis_client.get(cache_key)
    if cached_event:
        return json.loads(cached_event)

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    payload = serialize_event(event)
    await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload
