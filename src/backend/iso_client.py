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
        
        logger.info(f"Calling TravelTime API for {minutes} minutes at ({lat}, {lng})")
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Log raw API response structure for debugging
        logger.info(f"TravelTime API response keys: {list(data.keys())}")
        logger.info(f"TravelTime API response status: {response.status_code}")
        
        # Log full response structure at DEBUG level (coordinates may be large)
        # This helps diagnose parsing issues
        logger.debug(f"TravelTime API full response structure: {data}")
        
        # Log a summary of the response structure without full coordinates
        if "results" in data:
            results_summary = []
            for i, result in enumerate(data.get("results", [])[:3]):  # Limit to first 3 results
                result_summary = {"index": i, "keys": list(result.keys())}
                if "shapes" in result:
                    shapes_info = []
                    for j, shape in enumerate(result.get("shapes", [])[:3]):  # Limit to first 3 shapes
                        shape_info = {"index": j, "keys": list(shape.keys())}
                        if "shell" in shape:
                            shape_info["shell_length"] = len(shape.get("shell", []))
                        if "shells" in shape:
                            shape_info["shells_count"] = len(shape.get("shells", []))
                            if shape.get("shells"):
                                shape_info["first_shell_length"] = len(shape.get("shells", [])[0]) if shape.get("shells")[0] else 0
                        shapes_info.append(shape_info)
                    result_summary["shapes"] = shapes_info
                results_summary.append(result_summary)
            logger.info(f"TravelTime API response structure summary: {results_summary}")
        
        # Extract polygon from TravelTime response
        # TravelTime returns results in a specific format
        results = data.get("results", [])
        logger.info(f"Number of results in response: {len(results)}")
        
        if not results:
            logger.error("No isochrone results from TravelTime API")
            logger.error(f"Full response structure: {data}")
            raise ValueError(
                "TravelTime API returned no results. "
                "Check API credentials and request parameters."
            )
        
        # Get the first result
        result = results[0]
        logger.info(f"First result keys: {list(result.keys())}")
        
        # TravelTime API v4 can return shapes in different formats
        # Try to extract shapes from the result
        shapes = result.get("shapes", [])
        logger.info(f"Number of shapes in result: {len(shapes)}")
        
        # Alternative: check if result itself contains shell/holes directly
        if not shapes and ("shell" in result or "holes" in result or "shells" in result):
            logger.info("Found shell/holes directly in result, not in shapes array")
            shapes = [result]
        
        if not shapes:
            logger.error("No shapes found in TravelTime response")
            logger.error(f"Full response structure: {data}")
            logger.error(f"Result structure: {result}")
            raise ValueError(
                f"No shapes found in TravelTime API response. "
                f"Result keys: {list(result.keys())}. "
                f"Expected 'shapes' array or 'shell'/'shells' in result."
            )
        
        # TravelTime returns coordinates as [lng, lat] pairs in the shell
        # The shell is the outer boundary of the isochrone
        # TravelTime API v4 may return 'shell' (singular) or 'shells' (plural array)
        first_shape = shapes[0]
        logger.info(f"First shape keys: {list(first_shape.keys())}")
        
        # Try to extract shell coordinates - handle both 'shell' and 'shells'
        shell = None
        
        # Check for 'shell' (singular) - single outer boundary
        if "shell" in first_shape:
            shell = first_shape.get("shell", [])
            logger.info("Found 'shell' (singular) in shape")
        
        # Check for 'shells' (plural) - array of outer boundaries (multiple disconnected polygons)
        elif "shells" in first_shape:
            shells = first_shape.get("shells", [])
            logger.info(f"Found 'shells' (plural) in shape with {len(shells)} shell(s)")
            if shells and len(shells) > 0:
                # Use the first (largest) shell
                shell = shells[0]
                logger.info(f"Using first shell from shells array (length: {len(shell) if shell else 0})")
            else:
                logger.warning("'shells' array is empty")
        
        # Alternative: check if coordinates are in a different format
        if not shell:
            # Some API versions might return coordinates directly
            if "coordinates" in first_shape:
                logger.info("Found 'coordinates' key instead of 'shell'/'shells', attempting to use it")
                shell = first_shape.get("coordinates", [])
            elif "geometry" in first_shape and "coordinates" in first_shape.get("geometry", {}):
                logger.info("Found GeoJSON-style geometry, extracting coordinates")
                geom = first_shape.get("geometry", {})
                if geom.get("type") == "Polygon" and geom.get("coordinates"):
                    # GeoJSON Polygon format: coordinates is array of rings
                    shell = geom["coordinates"][0] if geom["coordinates"] else []
        
        # Log response structure if shell still not found
        if not shell:
            logger.error("Could not find shell coordinates in TravelTime API response")
            logger.error(f"Full response structure: {data}")
            logger.error(f"Result structure: {result}")
            logger.error(f"First shape structure: {first_shape}")
            raise ValueError(
                f"Could not extract shell coordinates from TravelTime API response. "
                f"Shape keys: {list(first_shape.keys())}. "
                f"Expected 'shell' or 'shells' key in shape object."
            )
        
        logger.info(f"Shell length: {len(shell) if shell else 0}")
        if shell and len(shell) > 0:
            first_coord = shell[0]
            logger.info(f"First shell coordinate: {first_coord} (type: {type(first_coord).__name__})")
            if isinstance(first_coord, dict):
                logger.info(f"First coordinate keys: {list(first_coord.keys())}")
            logger.info(f"Last shell coordinate: {shell[-1]}")
        
        if not shell or len(shell) < 3:
            logger.error(f"Invalid shell in TravelTime response (length: {len(shell) if shell else 0})")
            logger.error(f"Full response structure: {data}")
            logger.error(f"Result structure: {result}")
            logger.error(f"First shape structure: {first_shape}")
            raise ValueError(
                f"Invalid shell in TravelTime API response: shell length is {len(shell) if shell else 0}, "
                f"but need at least 3 coordinates for a valid polygon."
            )
        
        # Validate coordinates are numbers
        # TravelTime API may return coordinates as:
        # 1. Arrays: [lng, lat] or [lat, lng]
        # 2. Objects: {"lat": ..., "lng": ...} or {"lng": ..., "lat": ...}
        valid_coords = []
        invalid_count = 0
        coord_format = None  # Track which format we're seeing
        
        for i, coord in enumerate(shell):
            lng_val = None
            lat_val = None
            
            # Try to parse as array/tuple [lng, lat] or [lat, lng]
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    # Try [lng, lat] format first (GeoJSON standard)
                    lng_val = float(coord[0])
                    lat_val = float(coord[1])
                    # If lng is in valid lat range and lat is in valid lng range, might be swapped
                    if (-90 <= lng_val <= 90) and (-180 <= lat_val <= 180) and not (-90 <= lat_val <= 90):
                        # Likely swapped - swap them
                        logger.debug(f"Coordinate at index {i} appears swapped, correcting")
                        lng_val, lat_val = float(coord[1]), float(coord[0])
                    if coord_format is None:
                        coord_format = "array"
                except (ValueError, TypeError, IndexError) as e:
                    logger.debug(f"Failed to parse coordinate as array at index {i}: {coord} - {e}")
            
            # Try to parse as object {"lat": ..., "lng": ...} or {"lng": ..., "lat": ...}
            if (lng_val is None or lat_val is None) and isinstance(coord, dict):
                try:
                    # Try both key orders
                    if "lng" in coord and "lat" in coord:
                        lng_val = float(coord["lng"])
                        lat_val = float(coord["lat"])
                        if coord_format is None:
                            coord_format = "object_lng_lat"
                    elif "lat" in coord and "lng" in coord:
                        lat_val = float(coord["lat"])
                        lng_val = float(coord["lng"])
                        if coord_format is None:
                            coord_format = "object_lat_lng"
                    else:
                        logger.debug(f"Coordinate object at index {i} missing lat/lng keys: {list(coord.keys())}")
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"Failed to parse coordinate as object at index {i}: {coord} - {e}")
            
            # Validate the parsed values
            if lng_val is None or lat_val is None:
                if i < 5:  # Only log first few to avoid spam
                    logger.warning(f"Invalid coordinate at index {i}: {coord} (type: {type(coord)})")
                invalid_count += 1
                continue
            
            # Validate ranges
            if not (-180 <= lng_val <= 180) or not (-90 <= lat_val <= 90):
                if i < 5:  # Only log first few to avoid spam
                    logger.warning(f"Coordinate out of range at index {i}: lng={lng_val}, lat={lat_val}")
                invalid_count += 1
                continue
            
            # Valid coordinate - add as [lng, lat] for GeoJSON
            valid_coords.append([lng_val, lat_val])
        
        if coord_format:
            logger.info(f"Detected coordinate format: {coord_format}")
        
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid coordinates out of {len(shell)} total")
        
        if len(valid_coords) < 3:
            logger.error(f"Not enough valid coordinates ({len(valid_coords)}) after validation")
            logger.error(f"Full response structure: {data}")
            logger.error(f"Result structure: {result}")
            logger.error(f"First shape structure: {first_shape}")
            logger.error(f"Shell data: {shell[:5]}... (showing first 5 coordinates)")
            raise ValueError(
                f"Not enough valid coordinates after validation: {len(valid_coords)} "
                f"(need at least 3 for a valid polygon). "
                f"Found {invalid_count} invalid coordinates out of {len(shell)} total."
            )
        
        # Convert to GeoJSON format
        # Ensure polygon is closed (first point equals last point)
        coordinates = valid_coords
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
            logger.debug("Polygon was not closed, added closing point")
        
        logger.info(f"Final coordinate count: {len(coordinates)}")
        logger.debug(f"Coordinate bounds - Lng: [{min(c[0] for c in coordinates):.6f}, {max(c[0] for c in coordinates):.6f}], Lat: [{min(c[1] for c in coordinates):.6f}, {max(c[1] for c in coordinates):.6f}]")
        
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
        
        logger.info(f"Generated isochrone for {minutes} minutes at ({lat}, {lng}) with {len(coordinates)} points")
        logger.debug(f"GeoJSON structure: type={geojson['type']}, geometry.type={geojson['geometry']['type']}, coordinates.rings={len(geojson['geometry']['coordinates'])}")
        return geojson
        
    except requests.exceptions.RequestException as e:
        # Network/HTTP errors - these are actual API failures, not parsing issues
        logger.error(f"Error fetching isochrone from TravelTime API: {e}")
        logger.error(f"Request URL: {url}")
        logger.error(f"Request headers: {headers}")
        logger.error(f"Request body: {body}")
        raise ValueError(f"TravelTime API request failed: {str(e)}") from e
    except (KeyError, ValueError) as e:
        # Parsing/validation errors - log full response structure for debugging
        logger.error(f"Error parsing TravelTime API response: {e}")
        if 'data' in locals():
            logger.error(f"Full API response structure: {data}")
        raise ValueError(f"Failed to parse TravelTime API response: {str(e)}") from e
    except Exception as e:
        # Unexpected errors - log everything for debugging
        logger.error(f"Unexpected error in isochrone client: {e}", exc_info=True)
        if 'data' in locals():
            logger.error(f"Full API response structure: {data}")
        raise ValueError(f"Unexpected error processing TravelTime API response: {str(e)}") from e


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
    logger.info(f"Generating mock isochrone for {minutes} minutes at ({lat}, {lng})")
    
    # Approximate radius calculation
    # Rough conversion: 1 degree latitude ≈ 111 km
    # Average driving speed: ~60 km/h
    # 30 min = 30 km ≈ 0.27°, 45 min = 45 km ≈ 0.41°, 60 min = 60 km ≈ 0.54°
    # Using a scaling factor for better approximation
    radius_km = minutes * 1.0  # 1 km per minute (rough average)
    radius_degrees = radius_km / 111.0  # Convert km to degrees
    
    logger.debug(f"Mock polygon radius: {radius_km} km ({radius_degrees:.6f} degrees)")
    
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
        lng_val = float(lng + lng_offset)
        lat_val = float(lat + lat_offset)
        
        # Validate coordinates
        if not (-180 <= lng_val <= 180) or not (-90 <= lat_val <= 90):
            logger.warning(f"Mock coordinate out of range at angle {angle:.2f}: [{lng_val}, {lat_val}]")
            continue
        
        coordinates.append([lng_val, lat_val])
    
    if len(coordinates) < 3:
        logger.error(f"Mock polygon generation failed: only {len(coordinates)} valid coordinates")
        raise ValueError(f"Failed to generate valid mock polygon: only {len(coordinates)} coordinates")
    
    # Ensure polygon is closed
    if coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
        logger.debug("Mock polygon was not closed, added closing point")
    
    logger.info(f"Generated {len(coordinates)} coordinates for mock polygon")
    logger.debug(f"Mock coordinate bounds - Lng: [{min(c[0] for c in coordinates):.6f}, {max(c[0] for c in coordinates):.6f}], Lat: [{min(c[1] for c in coordinates):.6f}, {max(c[1] for c in coordinates):.6f}]")
    
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
    
    logger.info(f"Generated mock isochrone for {minutes} minutes at ({lat}, {lng}) with {len(coordinates)} points")
    logger.debug(f"Mock GeoJSON structure: type={geojson['type']}, geometry.type={geojson['geometry']['type']}, coordinates.rings={len(geojson['geometry']['coordinates'])}")
    return geojson
