import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from adapters.auth.router import require_sign_in
from adapters.auth.router import router as auth_router
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


# Deny by default: every router mounted here requires a sign-in. Only the
# routes mounted directly on `app` below are reachable without one.
gated = APIRouter(dependencies=[Depends(require_sign_in)])
gated.include_router(capture_router)
gated.include_router(notes_router)
gated.include_router(remember_router)

app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(auth_router)
if settings.environment_name != Environment.PROD:
    app.include_router(outbox_router)
app.include_router(gated)
app.add_exception_handler(CoreException, core_exception_handler)
