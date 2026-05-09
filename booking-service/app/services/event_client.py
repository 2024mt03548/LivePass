import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.schemas import EventResponse


settings = get_settings()


class EventClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def get_event(self, event_id: int) -> EventResponse:
        url = f"{self.base_url}/events/{event_id}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Event service is unavailable",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        if response.is_error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Event service returned an error",
            )

        return EventResponse.model_validate(response.json())


event_client = EventClient(settings.event_service_url)
