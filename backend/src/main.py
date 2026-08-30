from fastapi import FastAPI

from adapters.http.capture import router as capture_router
from adapters.http.errors import core_exception_handler
from adapters.http.health import router as health_router
from domain.exceptions import CoreException

app = FastAPI()
app.include_router(health_router)
app.include_router(capture_router)
app.add_exception_handler(CoreException, core_exception_handler)
