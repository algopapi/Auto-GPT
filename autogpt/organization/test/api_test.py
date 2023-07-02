import pytest
from fastapi.testclient import TestClient

from autogpt.organization.app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"message":"Hello POD!"}

@pytest.mark.asyncio
async def test_start():
    response = client.post("/api/v1/org_pod/start")
    assert response.status_code == 200
    assert response.json() == {"message": "Organization script started"}

@pytest.mark.asyncio
async def test_pause():
    response = client.post("/api/v1/org_pod/pause")
    assert response.status_code == 200
    assert response.json() == {"message": "Organization script paused"}

@pytest.mark.asyncio
async def test_resume():
    response = client.post("/api/v1/org_pod/resume")
    assert response.status_code == 200
    assert response.json() == {"message": "Organization script resumed"}
