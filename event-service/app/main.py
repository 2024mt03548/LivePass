from fastapi import FastAPI

from app.config import get_settings
from app.db import Base, engine
from app.routes.events import router as events_router
from app.routes.inventory import router as inventory_router


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "event-service"}


app.include_router(events_router)
app.include_router(inventory_router)
