"""
TravelTime Isochrones API client for generating drive-time polygons.
Returns GeoJSON polygon format for isochrone visualization.
"""
import logging
import math
from typing import Dict, Any
import requests
from config import TRAVELTIME_API_KEY, TRAVELTIME_APP_ID

logger = logging.getLogger(__name__)


def get_isochrone(lat: float, lng: float, minutes: int, mock: bool = False) -> Dict[str, Any]:
    """
    Get isochrone polygon from TravelTime API.
    
    Args:
        lat: Latitude of center point
        lng: Longitude of center point
        minutes: Travel time in minutes (30, 45, or 60)
        mock: If True, return mock polygon instead of calling API
        
    Returns:
        GeoJSON Feature with Polygon geometry:
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lng, lat], ...]]
            },
            "properties": {
                "minutes": 30,
                "center": [lng, lat],
                "mock": true/false
            }
        }
    """
    if mock:
        return _get_mock_polygon(lat, lng, minutes)
    
    if not TRAVELTIME_API_KEY or not TRAVELTIME_APP_ID:
        logger.warning("TravelTime API credentials not configured, using mock polygon")
        return _get_mock_polygon(lat, lng, minutes)
    
    try:
        # TravelTime API endpoint
        url = "https://api.traveltimeapp.com/v4/time-map"
        
        headers = {
            "Content-Type": "application/json",
            "X-Application-Id": TRAVELTIME_APP_ID,
            "X-Api-Key": TRAVELTIME_API_KEY
        }
        
        # TravelTime API request body
        # Travel time must be in seconds
        body = {
            "departure_searches": [
                {
                    "id": "isochrone",
                    "coords": {
                        "lat": float(lat),
                        "lng": float(lng)
                    },
                    "transportation": {
                        "type": "driving"
                    },
                    "travel_time": int(minutes * 60),  # Convert minutes to seconds
                    "departure_time": "2024-01-01T12:00:00Z"
                }
            ]
        }
        
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract polygon from TravelTime response
        # TravelTime returns results in a specific format
        results = data.get("results", [])
        if not results:
            logger.warning("No isochrone results from TravelTime API, using mock")
            return _get_mock_polygon(lat, lng, minutes)
        
        # Get the first result
        result = results[0]
        shapes = result.get("shapes", [])
        
        if not shapes:
            logger.warning("No shapes in TravelTime response, using mock")
            return _get_mock_polygon(lat, lng, minutes)
        
        # TravelTime returns coordinates as [lng, lat] pairs in the shell
        # The shell is the outer boundary of the isochrone
        shell = shapes[0].get("shell", [])
        
        if not shell or len(shell) < 3:
            logger.warning("Invalid shell in TravelTime response, using mock")
            return _get_mock_polygon(lat, lng, minutes)
        
        # Convert to GeoJSON format
        # Ensure polygon is closed (first point equals last point)
        coordinates = list(shell)
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        
        # GeoJSON Polygon format: coordinates is an array of linear rings
        # Each ring is an array of [lng, lat] coordinate pairs
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]  # Single ring polygon
            },
            "properties": {
                "minutes": minutes,
                "center": [float(lng), float(lat)],
                "mock": False
            }
        }
        
        logger.info(f"Generated isochrone for {minutes} minutes at ({lat}, {lng})")
        return geojson
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching isochrone from TravelTime API: {e}")
        logger.info("Falling back to mock polygon")
        return _get_mock_polygon(lat, lng, minutes)
    except KeyError as e:
        logger.error(f"Unexpected response structure from TravelTime API: {e}")
        logger.info("Falling back to mock polygon")
        return _get_mock_polygon(lat, lng, minutes)
    except Exception as e:
        logger.error(f"Unexpected error in isochrone client: {e}")
        logger.info("Falling back to mock polygon")
        return _get_mock_polygon(lat, lng, minutes)


def _get_mock_polygon(lat: float, lng: float, minutes: int) -> Dict[str, Any]:
    """
    Generate a mock isochrone polygon (approximate circle).
    Size scales with minutes (30/45/60).
    
    Args:
        lat: Latitude of center point
        lng: Longitude of center point
        minutes: Travel time in minutes
        
    Returns:
        GeoJSON Feature with Polygon geometry
    """
    # Approximate radius calculation
    # Rough conversion: 1 degree latitude ≈ 111 km
    # Average driving speed: ~60 km/h
    # 30 min = 30 km ≈ 0.27°, 45 min = 45 km ≈ 0.41°, 60 min = 60 km ≈ 0.54°
    # Using a scaling factor for better approximation
    radius_km = minutes * 1.0  # 1 km per minute (rough average)
    radius_degrees = radius_km / 111.0  # Convert km to degrees
    
    # Generate a polygon approximating a circle with multiple points
    num_points = 32  # More points = smoother circle
    coordinates = []
    
    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        
        # Calculate lat/lng offsets
        # Latitude offset is constant
        lat_offset = radius_degrees * math.cos(angle)
        
        # Longitude offset varies with latitude (longitude lines converge at poles)
        # At latitude lat, 1 degree longitude ≈ 111 km * cos(lat)
        lng_offset = radius_degrees * math.sin(angle) / math.cos(math.radians(lat))
        
        # Add to coordinates (GeoJSON uses [lng, lat] format)
        coordinates.append([
            float(lng + lng_offset),
            float(lat + lat_offset)
        ])
    
    # Ensure polygon is closed
    if coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coordinates]  # Single ring polygon
        },
        "properties": {
            "minutes": minutes,
            "center": [float(lng), float(lat)],
            "mock": True
        }
    }
    
    logger.info(f"Generated mock isochrone for {minutes} minutes at ({lat}, {lng})")
    return geojson
