from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LivePass Booking Service"
    environment: str = "development"
    debug: bool = False

    event_service_url: str = "http://event-service:8000"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    booking_queue: str = "booking.requested"
    booking_database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
