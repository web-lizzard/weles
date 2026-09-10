import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from adapters.compose import get_outbox_worker
from adapters.http.capture import router as capture_router
from adapters.http.errors import core_exception_handler
from adapters.http.health import router as health_router
from adapters.http.notes import router as notes_router
from adapters.http.outbox import router as outbox_router
from adapters.http.remember import router as remember_router
from config.settings import Environment, Settings
from domain.exceptions import CoreException

settings = Settings()  # pyright: ignore[reportCallIssue]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    worker = get_outbox_worker()
    task = asyncio.create_task(
        worker.run_forever(settings.outbox_poll_interval_seconds)
    )
    try:
        yield
    finally:
        _ = task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(capture_router)
app.include_router(notes_router)
app.include_router(remember_router)
if settings.environment_name != Environment.PROD:
    app.include_router(outbox_router)
app.add_exception_handler(CoreException, core_exception_handler)
