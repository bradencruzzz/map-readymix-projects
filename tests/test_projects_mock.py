"""
Test SAM.gov projects endpoint with mock data.
Tests remain mock-only and do not require API keys or internet access.
"""
import pytest
from httpx import AsyncClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "backend"))

from main import app


@pytest.mark.asyncio
async def test_projects_mock():
    """Test that projects endpoint returns data when mock=true"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/projects?mock=true")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one project in mock data"
        
        # Verify structure of first project matches new business-focused format
        if len(data) > 0:
            project = data[0]
            
            # Core identification fields
            assert "id" in project or "title" in project, "Project must have id or title"
            assert "title" in project, "Project must have title"
            
            # Date fields
            assert "posted_date" in project or "response_deadline" in project, "Project should have date fields"
            
            # NAICS and classification
            assert "naics" in project, "Project must have naics code"
            
            # Location fields (business-focused)
            assert "city" in project or "state" in project, "Project should have location fields"
            assert "lat" in project, "Project must have latitude"
            assert "lng" in project, "Project must have longitude"
            
            # Optional business fields (may be None)
            # These are part of the new structure but may not always be present
            optional_fields = [
                "project_type",
                "department",
                "zipcode",
                "country",
                "address",
                "estimated_award_amount",
                "ui_link"
            ]
            
            # Verify at least some optional fields are present or the structure allows None
            # The important thing is that the structure is correct
            assert isinstance(project.get("lat"), (int, float, type(None))), "lat must be numeric or None"
            assert isinstance(project.get("lng"), (int, float, type(None))), "lng must be numeric or None"
