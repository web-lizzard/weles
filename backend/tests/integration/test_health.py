import httpx
import pytest
from httpx import ASGITransport

from backend.main import app


@pytest.mark.asyncio
async def test_health_returns_ok_status() -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
