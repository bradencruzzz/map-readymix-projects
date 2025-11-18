"""
Test isochrones endpoint with mock data.
"""
import pytest
from httpx import AsyncClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

from main import app


@pytest.mark.asyncio
async def test_isochrones_stub():
    """Test that isochrones endpoint returns valid polygon structure when mock=true"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with Richmond, VA coordinates
        response = await client.get(
            "/api/isochrones?lat=37.5407&lng=-77.4360&minutes=30&mock=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify GeoJSON structure
        assert "type" in data
        assert data["type"] == "Feature"
        
        assert "geometry" in data
        geometry = data["geometry"]
        assert geometry["type"] == "Polygon"
        
        assert "coordinates" in geometry
        coordinates = geometry["coordinates"]
        assert isinstance(coordinates, list)
        assert len(coordinates) > 0
        
        # Verify polygon ring structure
        ring = coordinates[0]
        assert isinstance(ring, list)
        assert len(ring) > 3  # At least 4 points for a polygon
        
        # Verify coordinates are [lng, lat] pairs
        for coord in ring:
            assert isinstance(coord, list)
            assert len(coord) == 2
            assert isinstance(coord[0], (int, float))  # lng
            assert isinstance(coord[1], (int, float))  # lat
        
        # Verify properties
        assert "properties" in data
        props = data["properties"]
        assert "minutes" in props
        assert props["minutes"] == 30
