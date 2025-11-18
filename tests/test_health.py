"""
Test health endpoint.
"""
import pytest
from httpx import AsyncClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

from main import app


@pytest.mark.asyncio
async def test_health():
    """Test that health endpoint returns 200 and 'ok' status"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
