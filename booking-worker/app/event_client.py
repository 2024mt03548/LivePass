import asyncio
import logging

import httpx

from app.schemas import InventoryReservation


logger = logging.getLogger("booking-worker.event-client")


class EventServiceClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        retry_attempts: int,
        retry_backoff_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def reserve_inventory(
        self,
        event_id: int,
        tickets: int,
    ) -> InventoryReservation:
        url = f"{self.base_url}/internal/inventory/reserve"
        payload = {"event_id": event_id, "tickets": tickets}

        for attempt in range(1, self.retry_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, json=payload)
                response.raise_for_status()
                return InventoryReservation.model_validate(response.json())
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning(
                    "event_service_reserve_failed",
                    extra={
                        "event_id": event_id,
                        "tickets": tickets,
                        "attempt": attempt,
                        "max_attempts": self.retry_attempts,
                        "error": str(exc),
                    },
                )
                if attempt == self.retry_attempts:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * attempt)

        raise RuntimeError("event service reservation retry loop exited unexpectedly")
