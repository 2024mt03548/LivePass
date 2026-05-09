from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "LivePass Booking Worker"
    environment: str = "development"

    database_url: str
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    booking_queue: str = "booking.requested"
    event_service_url: str = "http://event-service:8000"
    event_service_timeout_seconds: float = 5.0
    event_service_retry_attempts: int = 3
    event_service_retry_backoff_seconds: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
