"""
FastAPI main application for Site Scout Lite.
Serves API endpoints and static frontend files.
"""
import logging
from datetime import date, timedelta
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sys
import os
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sam_client import fetch_projects, fetch_live_projects
from iso_client import get_isochrone
from places_client import search_places
from config import GOOGLE_MAPS_API_KEY

# Configure structured logging - set to DEBUG to see detailed diagnostic info
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Site Scout Lite API", version="1.0.0")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Serve the main index.html file with Google Maps API key injected"""
    frontend_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_file):
        # Read the HTML file
        with open(frontend_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace the placeholder API key with the actual key from environment
        api_key = GOOGLE_MAPS_API_KEY
        if not api_key:
            logger.error("GOOGLE_MAPS_API_KEY is not set in .env file. Google Maps will not work.")
            # Don't use placeholder - let it fail clearly
            api_key = ""
        else:
            logger.info("Injecting Google Maps API key into frontend")
        
        html_content = html_content.replace("YOUR_API_KEY", api_key)
        
        # Return the modified HTML
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    return {"message": "Frontend not found"}


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/api/projects")
async def get_projects(
    q: Optional[str] = Query(None, description="Search query (keyword or NAICS code)"),
    search_type: Optional[str] = Query("keyword", description="Search type: 'keyword' or 'naics'"),
    mock: Optional[bool] = Query(False, description="Use mock data (set to 'true' for mock mode)")
):
    """
    Fetch SAM.gov projects filtered by keyword search or NAICS code and Virginia state.
    
    Default behavior is to use live SAM.gov API. Set mock=true to use demo data.
    
    Args:
        q: Optional search query. Can be a keyword (e.g., "concrete", "cement") or NAICS code (e.g., "327300")
        search_type: Type of search - "keyword" (default) or "naics"
        mock: Optional query parameter. Set to 'true' to use mock data from sample_sam.json
        
    Returns:
        List of normalized project objects. Each project contains:
        - id: Notice ID
        - title: Project title
        - posted_date: Date posted
        - response_deadline: Response deadline
        - naics: NAICS code
        - project_type: Project type (e.g., "Award Notice")
        - department: Department/agency name
        - city: City location
        - state: State location
        - zipcode: ZIP code
        - country: Country code
        - address: Full address string
        - lat: Latitude (geocoded)
        - lng: Longitude (geocoded)
        - estimated_award_amount: Estimated award amount (float)
        - ui_link: UI link to SAM.gov opportunity
    """
    if mock:
        # Use mock data from sample_sam.json only when explicitly requested
        projects = fetch_projects(mock=True)
        logger.info(f"Returning {len(projects)} mock projects (mock=true)")
        return projects
    else:
        # Default: Use live SAM.gov API with date range (last 90 days)
        # No fallback to mock - errors should be raised
        today = date.today()
        posted_to = today
        posted_from = today - timedelta(days=90)
        
        try:
            # Determine search type and extract query - handle None and empty strings safely
            search_query = None
            if q:
                if isinstance(q, str):
                    search_query = q.strip() if q.strip() else None
                else:
                    search_query = str(q).strip() if str(q).strip() else None
            
            search_type_lower = (search_type.lower() if search_type and isinstance(search_type, str) else "keyword")
            
            keyword_query = None
            naics_query = None
            
            if search_query:
                if search_type_lower == "naics":
                    naics_query = search_query
                    logger.info(f"Searching by NAICS code: {naics_query}")
                else:
                    keyword_query = search_query
                    logger.info(f"Searching by keyword: {keyword_query}")
            
            projects = fetch_live_projects(
                posted_from=posted_from,
                posted_to=posted_to,
                limit=50,
                keyword=keyword_query,
                naics_code=naics_query,
                ptype="a"  # Award Notice type
            )
            
            search_desc = f"{search_type_lower}: {search_query}" if search_query else "all"
            logger.info(f"Returning {len(projects)} live projects from SAM.gov ({search_desc})")
            return projects
        except RuntimeError as e:
            # RuntimeError from SAM client (e.g., missing API key, rate limit)
            logger.error(f"Runtime error in /api/projects: {e}")
            # Check if it's a rate limit error
            error_msg = str(e).lower()
            logger.debug(f"Error message (lowercased): {error_msg}")
            is_rate_limit = (
                "rate limit" in error_msg or 
                "429" in error_msg or 
                "too many requests" in error_msg or
                "rate limit exceeded" in error_msg
            )
            logger.debug(f"Is rate limit error: {is_rate_limit}")
            if is_rate_limit:
                logger.info("Returning 429 status code for rate limit error")
                raise HTTPException(status_code=429, detail=str(e))
            logger.info("Returning 500 status code for non-rate-limit RuntimeError")
            raise HTTPException(status_code=500, detail=str(e))
        except requests.exceptions.HTTPError as e:
            # HTTP errors from SAM.gov API
            status_code = e.response.status_code if e.response else 500
            logger.error(f"HTTP error calling SAM.gov API: {status_code} - {e}")
            # Preserve the original status code if it's a client error (4xx)
            if status_code and 400 <= status_code < 500:
                raise HTTPException(
                    status_code=status_code,
                    detail=f"SAM.gov API error: {status_code} - {str(e)}"
                )
            raise HTTPException(
                status_code=500, 
                detail=f"SAM.gov API error: {status_code} - {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            # Network/timeout errors
            logger.error(f"Network error calling SAM.gov API: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Network error connecting to SAM.gov API: {str(e)}"
            )
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected error in /api/projects (live mode): {e}", exc_info=True)
            import traceback
            error_detail = f"Error fetching projects from SAM.gov: {str(e)}"
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_detail)


@app.get("/api/isochrones")
async def get_isochrones(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    minutes: int = Query(30, description="Travel time in minutes (30, 45, or 60)"),
    mock: Optional[bool] = Query(False, description="Use mock data (set to 'true' for mock mode)")
):
    """
    Generate isochrone polygon for given location and travel time.
    
    Args:
        lat: Latitude of center point
        lng: Longitude of center point
        minutes: Travel time in minutes (30, 45, or 60)
        mock: Optional query parameter. Set to 'true' to return mock polygon
        
    Returns:
        GeoJSON Feature with polygon geometry
    """
    try:
        # Validate minutes
        if minutes not in [30, 45, 60]:
            raise HTTPException(
                status_code=400,
                detail="minutes must be 30, 45, or 60"
            )
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise HTTPException(
                status_code=400,
                detail="Invalid coordinates"
            )
        
        isochrone = get_isochrone(lat, lng, minutes, mock=mock)
        logger.info(f"Generated isochrone for ({lat}, {lng}), {minutes} min (mock={mock})")
        return isochrone
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/isochrones: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating isochrone: {str(e)}")


@app.get("/api/places")
async def get_places(
    q: str = Query(..., description="Search query"),
    mock: Optional[bool] = Query(False, description="Use mock data (set to 'true' for mock mode)")
):
    """
    Search for competitor facilities using Google Places API.
    
    Args:
        q: Search query string
        mock: Optional query parameter. Set to 'true' to use mock data
        
    Returns:
        List of places with name, lat, lng
    """
    try:
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
        
        places = search_places(q.strip(), mock=mock)
        logger.info(f"Found {len(places)} places for query: {q} (mock={mock})")
        return places
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/places: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching places: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
