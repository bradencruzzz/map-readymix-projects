"""
Google Places API client for competitor facility lookup.
Uses Google Places TextSearch API to find competitor locations.
"""
import logging
from typing import List, Dict, Any
import requests
from config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)


def search_places(query: str, mock: bool = False) -> List[Dict[str, Any]]:
    """
    Search for places using Google Places TextSearch API.
    
    Args:
        query: Search query string (e.g., "Vulcan Materials")
        mock: If True, return mock data instead of calling API
        
    Returns:
        Simplified list of places:
        [
            {
                "name": "Vulcan Materials",
                "address": "123 Main St, Richmond, VA 23220",
                "lat": 37.5407,
                "lng": -77.4360
            },
            ...
        ]
    """
    if mock:
        return _get_mock_places(query)
    
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not configured, using mock data")
        return _get_mock_places(query)
    
    try:
        # Google Places TextSearch API endpoint
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            "query": query.strip(),
            "key": GOOGLE_MAPS_API_KEY,
            "region": "us"  # Bias to US results
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Check API response status
        status = data.get("status")
        if status != "OK":
            error_message = data.get("error_message", "Unknown error")
            logger.warning(f"Google Places API returned status: {status} - {error_message}")
            return _get_mock_places(query)
        
        places = []
        results = data.get("results", [])
        
        for result in results:
            try:
                # Extract location from geometry
                geometry = result.get("geometry", {})
                location = geometry.get("location", {})
                
                lat = location.get("lat")
                lng = location.get("lng")
                
                # Only include places with valid coordinates
                if lat is not None and lng is not None:
                    # Extract formatted address from result
                    address = result.get("formatted_address", "")
                    
                    place = {
                        "name": result.get("name", "Unknown"),
                        "address": address,
                        "lat": float(lat),
                        "lng": float(lng)
                    }
                    places.append(place)
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"Error processing place result: {e}")
                continue
        
        logger.info(f"Found {len(places)} places for query: '{query}'")
        return places
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching places from Google Places API: {e}")
        logger.info("Falling back to mock data")
        return _get_mock_places(query)
    except KeyError as e:
        logger.error(f"Unexpected response structure from Google Places API: {e}")
        logger.info("Falling back to mock data")
        return _get_mock_places(query)
    except Exception as e:
        logger.error(f"Unexpected error in places client: {e}")
        logger.info("Falling back to mock data")
        return _get_mock_places(query)


def _get_mock_places(query: str) -> List[Dict[str, Any]]:
    """
    Return mock competitor data for testing.
    All locations are in Virginia.
    
    Args:
        query: Search query string (used for filtering mock results)
        
    Returns:
        List of places with name, address, lat, lng
    """
    # Sample competitor locations in Virginia
    mock_competitors = [
        {"name": "Vulcan Materials - Richmond", "address": "Richmond, VA 23220", "lat": 37.5407, "lng": -77.4360},
        {"name": "Martin Marietta - Norfolk", "address": "Norfolk, VA 23510", "lat": 36.8468, "lng": -76.2852},
        {"name": "LafargeHolcim - Roanoke", "address": "Roanoke, VA 24011", "lat": 37.2710, "lng": -79.9414},
        {"name": "Cemex - Alexandria", "address": "Alexandria, VA 22314", "lat": 38.8048, "lng": -77.0469},
        {"name": "Vulcan Materials - Virginia Beach", "address": "Virginia Beach, VA 23451", "lat": 36.8529, "lng": -75.9780},
        {"name": "Martin Marietta - Charlottesville", "address": "Charlottesville, VA 22903", "lat": 38.0293, "lng": -78.4767},
    ]
    
    # Filter by query if provided
    if query and query.strip():
        query_lower = query.strip().lower()
        filtered = [
            comp for comp in mock_competitors
            if query_lower in comp["name"].lower()
        ]
        if filtered:
            logger.info(f"Mock: Found {len(filtered)} places matching query '{query}'")
            return filtered
    
    # Return first 3 if no query match or no query
    logger.info(f"Mock: Returning {min(3, len(mock_competitors))} default competitor locations")
    return mock_competitors[:3]
