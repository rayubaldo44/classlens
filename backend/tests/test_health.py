import asyncio

import httpx

from app.main import app


def test_health_returns_stable_contract() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "classlens-api"}


def test_health_allows_local_vite_origin() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health", headers={"Origin": "http://localhost:5173"})

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
