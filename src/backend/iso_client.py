"""
TravelTime Isochrones API client for generating drive-time polygons.
Returns GeoJSON polygon format for isochrone visualization.
"""
import logging
import math
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import requests
from config import TRAVELTIME_API_KEY, TRAVELTIME_APP_ID

logger = logging.getLogger(__name__)


def _point_in_polygon(lng: float, lat: float, polygon: list) -> bool:
    """
    Check if a point is inside a polygon using the ray casting algorithm.
    
    Args:
        lng: Longitude of the point
        lat: Latitude of the point
        polygon: List of [lng, lat] coordinate pairs forming a closed polygon
        
    Returns:
        True if point is inside polygon, False otherwise
    """
    if not polygon or len(polygon) < 3:
        return False
    
    # Remove duplicate closing point if present
    coords = polygon[:-1] if polygon[0] == polygon[-1] else polygon
    
    n = len(coords)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        
        # Check if ray crosses edge
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def _min_distance_to_polygon(lng: float, lat: float, polygon: list) -> float:
    """
    Calculate the minimum distance from a point to the polygon boundary.
    
    Args:
        lng: Longitude of the point
        lat: Latitude of the point
        polygon: List of [lng, lat] coordinate pairs forming a closed polygon
        
    Returns:
        Minimum distance in degrees
    """
    if not polygon or len(polygon) < 3:
        return float('inf')
    
    # Remove duplicate closing point if present
    coords = polygon[:-1] if polygon[0] == polygon[-1] else polygon
    
    min_dist = float('inf')
    n = len(coords)
    
    for i in range(n):
        # Get edge endpoints
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        
        # Calculate distance from point to line segment
        # Using simplified distance calculation (approximate for small distances)
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Edge is a point
            dist = math.sqrt((lng - x1) ** 2 + (lat - y1) ** 2)
        else:
            # Project point onto line segment
            t = max(0, min(1, ((lng - x1) * dx + (lat - y1) * dy) / (dx * dx + dy * dy)))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            
            # Distance from point to projection
            dist = math.sqrt((lng - proj_x) ** 2 + (lat - proj_y) ** 2)
        
        min_dist = min(min_dist, dist)
    
    return min_dist


LATITUDE_KEYS = {"lat", "latitude", "y", "y_coord", "geo_lat", "center_lat"}
LONGITUDE_KEYS = {"lng", "lon", "long", "longitude", "x", "x_coord", "geo_lng", "center_lng"}


def _coerce_float(value: Any) -> Optional[float]:
    try:
        warnings = []
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_lat_lng_from_object(obj: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    lat = None
    lng = None
    for key, val in obj.items():
        key_lower = key.lower()
        if key_lower in LATITUDE_KEYS and lat is None:
            lat = _coerce_float(val)
        elif key_lower in LONGITUDE_KEYS and lng is None:
            lng = _coerce_float(val)
    return lat, lng


def _convert_shell_to_coordinates(shell_data: Any, context: str, max_warning_logs: int = 5) -> Tuple[list, int, Optional[str]]:
    """
    Normalize raw TravelTime shell coordinates into GeoJSON-friendly [lng, lat] pairs.
    Returns (valid_coords, invalid_count, coord_format)
    """
    valid_coords = []
    invalid_count = 0
    coord_format = None

    if not isinstance(shell_data, (list, tuple)):
        logger.warning(f"[Isochrone] Shell data '{context}' is not a list/tuple (type={type(shell_data).__name__})")
        return valid_coords, invalid_count, coord_format

    for idx, coord in enumerate(shell_data):
        lng_val = None
        lat_val = None

        if isinstance(coord, dict):
            lat_candidate, lng_candidate = _extract_lat_lng_from_object(coord)
            if lat_candidate is not None and lng_candidate is not None:
                lat_val = lat_candidate
                lng_val = lng_candidate
                if coord_format is None:
                    coord_format = "object"
        elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
            # CRITICAL: TravelTime API v4 documentation is unclear about coordinate order
            # We'll parse as [lng, lat] (GeoJSON standard) initially, then detect swaps later
            # The swap detection happens after parsing by checking if center is in bounds
            lng_val = _coerce_float(coord[0])
            lat_val = _coerce_float(coord[1])
            if coord_format is None:
                coord_format = "array"
        else:
            invalid_count += 1
            if invalid_count <= max_warning_logs:
                logger.warning(f"[Isochrone] Invalid coordinate ({context}) at index {idx}: {coord}")
            continue

        if lng_val is None or lat_val is None:
            invalid_count += 1
            if invalid_count <= max_warning_logs:
                logger.warning(f"[Isochrone] Missing lat/lng ({context}) at index {idx}: {coord}")
            continue

        if not (-180 <= lng_val <= 180) or not (-90 <= lat_val <= 90):
            invalid_count += 1
            if invalid_count <= max_warning_logs:
                logger.warning(f"[Isochrone] Coordinate out of range ({context}) idx {idx}: lng={lng_val}, lat={lat_val}")
            continue

        valid_coords.append([lng_val, lat_val])

    return valid_coords, invalid_count, coord_format


def _compute_bounds(coords: list) -> Dict[str, float]:
    lng_values = [c[0] for c in coords]
    lat_values = [c[1] for c in coords]
    return {
        "lng_min": min(lng_values),
        "lng_max": max(lng_values),
        "lat_min": min(lat_values),
        "lat_max": max(lat_values),
    }


def _bounds_contain_point(bounds: Dict[str, float], lng: float, lat: float) -> bool:
    return (
        bounds["lng_min"] <= lng <= bounds["lng_max"] and
        bounds["lat_min"] <= lat <= bounds["lat_max"]
    )


def _ensure_closed_ring(coords: list) -> list:
    if not coords:
        return coords
    if coords[0] != coords[-1]:
        return coords + [coords[0]]
    return coords


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
        logger.error("TravelTime API credentials not configured!")
        logger.error(f"  TRAVELTIME_API_KEY present: {bool(TRAVELTIME_API_KEY)}")
        logger.error(f"  TRAVELTIME_APP_ID present: {bool(TRAVELTIME_APP_ID)}")
        logger.warning("  → Falling back to mock polygon")
        return _get_mock_polygon(lat, lng, minutes)
    
    # Initialize warnings list for collecting API response warnings
    warnings = []
    
    try:
        # TravelTime API endpoint - time-map is a POST endpoint
        url = "https://api.traveltimeapp.com/v4/time-map"
        
        headers = {
            "Content-Type": "application/json",
            "X-Application-Id": TRAVELTIME_APP_ID,
            "X-Api-Key": TRAVELTIME_API_KEY
        }
        
        # TravelTime API request body for POST endpoint
        # Based on documentation: https://docs.traveltime.com/api/reference/time-map
        body = {
            "locations": [
                {
                    "id": "origin",
                    "coords": {
                        "lat": float(lat),
                        "lng": float(lng)
                    }
                }
            ],
            "departure_searches": [
                {
                    "id": "isochrone",
                    "coords": {
                        "lat": float(lat),
                        "lng": float(lng)
                    },
                    "departure_time": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                    "travel_time": int(minutes * 60),  # Convert minutes to seconds
                    "transportation": {
                        "type": "driving"
                    }
                }
            ]
        }
        
        logger.info(f"Calling TravelTime API (POST) for {minutes} minutes at ({lat}, {lng})")
        logger.info(f"API request: coords={{lat: {lat}, lng: {lng}}}, transportation=driving, travel_time={int(minutes * 60)}s")
        logger.debug(f"Full API request body: {body}")
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
        
        center_lng = float(lng)
        center_lat = float(lat)

        first_shape = shapes[0]
        logger.info(f"First shape keys: {list(first_shape.keys())}")

        candidate_shells = []

        if "shell" in first_shape:
            candidate_shells.append(("shell", first_shape.get("shell", [])))
            logger.info("Found 'shell' (singular) in shape")

        if "shells" in first_shape:
            shells = first_shape.get("shells", [])
            logger.info(f"Found 'shells' (plural) in shape with {len(shells)} shell(s)")
            for idx, shell_entry in enumerate(shells):
                candidate_shells.append((f"shells[{idx}]", shell_entry))

        if not candidate_shells and "coordinates" in first_shape:
            logger.info("Found 'coordinates' key instead of 'shell'/'shells', attempting to use it")
            candidate_shells.append(("coordinates", first_shape.get("coordinates", [])))

        if not candidate_shells and "geometry" in first_shape:
            geom = first_shape.get("geometry", {})
            if geom.get("type") == "Polygon" and geom.get("coordinates"):
                candidate_shells.append(("geometry.coordinates[0]", geom["coordinates"][0]))

        if not candidate_shells:
            logger.error("No shell data found in TravelTime response shape")
            raise ValueError("Could not locate shell/shells/coordinates data in TravelTime API response.")

        candidate_coords = []
        for label, raw_shell in candidate_shells:
            coords, invalid_count, coord_format = _convert_shell_to_coordinates(raw_shell, context=label)
            if invalid_count > 0:
                warnings.append(f"{invalid_count} invalid coordinates removed from TravelTime response ({label})")
            if len(coords) < 3:
                logger.warning(f"[Isochrone] Candidate shell '{label}' discarded (only {len(coords)} valid coords)")
                continue
            
            # Check if coordinates might be swapped by testing both orientations
            bounds = _compute_bounds(coords)
            center_in_bounds = _bounds_contain_point(bounds, center_lng, center_lat)
            
            # If center is not in bounds, try swapping coordinates
            if not center_in_bounds:
                logger.debug(f"[Isochrone] Center not in bounds for '{label}', checking if coordinates are swapped")
                # Try swapping: if coords are [lat, lng], swap to [lng, lat]
                swapped_coords = [[c[1], c[0]] for c in coords]  # Swap lat/lng
                swapped_bounds = _compute_bounds(swapped_coords)
                swapped_center_in_bounds = _bounds_contain_point(swapped_bounds, center_lng, center_lat)
                
                if swapped_center_in_bounds:
                    logger.info(f"[Isochrone] Coordinates were swapped! Using swapped coordinates for '{label}'")
                    coords = swapped_coords
                    bounds = swapped_bounds
                    coord_format = f"{coord_format}_swapped" if coord_format else "swapped"
                else:
                    logger.debug(f"[Isochrone] Center still not in bounds after swapping for '{label}'")
            
            candidate_coords.append({
                "label": label,
                "coords": coords,
                "bounds": bounds,
                "coord_format": coord_format,
            })

        if not candidate_coords:
            logger.error("All candidate shells were invalid after coordinate normalization")
            raise ValueError("Unable to extract a valid polygon ring from TravelTime response.")

        selected_candidate = None
        selection_reason = ""

        for candidate in candidate_coords:
            ring = _ensure_closed_ring(candidate["coords"])
            if _point_in_polygon(center_lng, center_lat, ring):
                selected_candidate = candidate
                selection_reason = f"{candidate['label']} (center covered)"
                break

        if not selected_candidate:
            for candidate in candidate_coords:
                if _bounds_contain_point(candidate["bounds"], center_lng, center_lat):
                    selected_candidate = candidate
                    selection_reason = f"{candidate['label']} (bbox overlap)"
                    break

        if not selected_candidate:
            selected_candidate = max(candidate_coords, key=lambda c: len(c["coords"]))
            selection_reason = f"{selected_candidate['label']} (fallback longest ring)"

        logger.info(f"Selected shell: {selected_candidate['label']} - reason: {selection_reason}")
        logger.debug(f"Selected shell bounds: {selected_candidate['bounds']}")

        valid_coords = list(selected_candidate["coords"])
        coord_format = selected_candidate["coord_format"]
        
        # Convert to GeoJSON format
        # Ensure polygon is closed (first point equals last point)
        coordinates = valid_coords
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
            logger.debug("Polygon was not closed, added closing point")
        
        logger.info(f"Final coordinate count: {len(coordinates)}")
        
        # Calculate bounding box of isochrone
        lng_min = min(c[0] for c in coordinates)
        lng_max = max(c[0] for c in coordinates)
        lat_min = min(c[1] for c in coordinates)
        lat_max = max(c[1] for c in coordinates)
        
        logger.debug(f"Coordinate bounds - Lng: [{lng_min:.6f}, {lng_max:.6f}], Lat: [{lat_min:.6f}, {lat_max:.6f}]")
        
        # Log center point and bounds for debugging
        logger.info(f"Center point: ({center_lat:.6f}, {center_lng:.6f})")
        logger.info(f"Isochrone bounds: Lng[{lng_min:.6f}, {lng_max:.6f}], Lat[{lat_min:.6f}, {lat_max:.6f}]")
        
        # Calculate distance from center to bounding box center
        bbox_center_lng = (lng_min + lng_max) / 2
        bbox_center_lat = (lat_min + lat_max) / 2
        bbox_offset_lng = abs(center_lng - bbox_center_lng)
        bbox_offset_lat = abs(center_lat - bbox_center_lat)
        logger.debug(f"BBox center: ({bbox_center_lat:.6f}, {bbox_center_lng:.6f})")
        logger.debug(f"Center offset from bbox center: Lng={bbox_offset_lng:.6f}, Lat={bbox_offset_lat:.6f}")
        
        # First check if center is within bounding box (quick check)
        center_in_bbox = (lng_min <= center_lng <= lng_max) and (lat_min <= center_lat <= lat_max)
        
        if not center_in_bbox:
            # Calculate how far outside the bbox the center is
            lng_offset = 0
            lat_offset = 0
            if center_lng < lng_min:
                lng_offset = lng_min - center_lng
            elif center_lng > lng_max:
                lng_offset = center_lng - lng_max
            if center_lat < lat_min:
                lat_offset = lat_min - center_lat
            elif center_lat > lat_max:
                lat_offset = center_lat - lat_max
            
            logger.warning(
                f"WARNING: Center point ({center_lat:.6f}, {center_lng:.6f}) is NOT within isochrone bounding box. "
                f"BBox: Lng[{lng_min:.6f}, {lng_max:.6f}], Lat[{lat_min:.6f}, {lat_max:.6f}]. "
                f"Offset: Lng={lng_offset:.6f}°, Lat={lat_offset:.6f}° "
                f"(≈{lng_offset*111:.1f}km E/W, {lat_offset*111:.1f}km N/S). "
                f"This indicates a significant offset issue - the isochrone may be in the wrong location."
            )
            warnings.append(
                "Isochrone polygon does not enclose the requested center point. "
                "TravelTime API may have returned an offset polygon."
            )
        
        # More precise check: is center within the polygon itself
        center_in_polygon = _point_in_polygon(center_lng, center_lat, coordinates)
        
        if not center_in_polygon:
            # Calculate distance from center to nearest polygon edge
            min_distance = _min_distance_to_polygon(center_lng, center_lat, coordinates)
            logger.warning(
                f"WARNING: Center point ({center_lat}, {center_lng}) is NOT within the isochrone polygon. "
                f"Minimum distance to polygon edge: {min_distance:.6f} degrees. "
                f"This suggests the isochrone may not be properly centered on the departure point."
            )
            warnings.append(
                f"Isochrone polygon does not contain the marker. Offset ≈ {min_distance*111:.1f} km. "
                "Consider verifying the coordinates or retrying the request."
            )
            # If the center is very close (within 0.01 degrees ≈ 1.1 km), it's likely a minor offset
            # If it's far away, there's a more serious issue
            if min_distance > 0.01:
                logger.error(
                    f"ERROR: Center point is {min_distance:.6f} degrees away from isochrone. "
                    f"This is a significant offset and may indicate an API issue."
                )
        else:
            logger.info(f"Center point ({center_lat}, {center_lng}) is within the isochrone polygon ✓")
        
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
                "center": [center_lng, center_lat],
                "mock": False,
                "warnings": warnings,
                "selection_reason": selection_reason,
                "shell_label": selected_candidate["label"]
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
        raise ValueError(f"TravelTime API request failed: {str(e)}") from e
    except (KeyError, ValueError) as e:
        # Parsing/validation errors - log full response structure for debugging
        logger.error("=" * 80)
        logger.error(f"ERROR parsing TravelTime API response: {e}")
        logger.error("=" * 80)
        if 'data' in locals():
            logger.error(f"Full API response structure:")
            logger.error(f"  Type: {type(data)}")
            if isinstance(data, dict):
                logger.error(f"  Top-level keys: {list(data.keys())}")
                if "results" in data:
                    results = data.get("results", [])
                    logger.error(f"  Number of results: {len(results)}")
                    if results:
                        first_result = results[0]
                        logger.error(f"  First result keys: {list(first_result.keys()) if isinstance(first_result, dict) else 'NOT A DICT'}")
                        if isinstance(first_result, dict) and "shapes" in first_result:
                            shapes = first_result.get("shapes", [])
                            logger.error(f"  Number of shapes: {len(shapes)}")
                            if shapes:
                                first_shape = shapes[0]
                                logger.error(f"  First shape keys: {list(first_shape.keys()) if isinstance(first_shape, dict) else 'NOT A DICT'}")
            else:
                logger.error(f"  Response is not a dict: {str(data)[:500]}")
        if 'result' in locals():
            logger.error(f"Result structure: {result}")
        if 'first_shape' in locals():
            logger.error(f"First shape structure: {first_shape}")
        logger.error("=" * 80)
        raise ValueError(f"Failed to parse TravelTime API response: {str(e)}") from e
    except Exception as e:
        # Unexpected errors - log everything for debugging
        logger.error("=" * 80)
        logger.error(f"UNEXPECTED ERROR in isochrone client: {e}")
        logger.error("=" * 80)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        if 'data' in locals():
            logger.error(f"Full API response structure:")
            logger.error(f"  Type: {type(data)}")
            if isinstance(data, dict):
                logger.error(f"  Top-level keys: {list(data.keys())}")
            else:
                logger.error(f"  Response is not a dict: {str(data)[:500]}")
        if 'result' in locals():
            logger.error(f"Result structure: {result}")
        if 'first_shape' in locals():
            logger.error(f"First shape structure: {first_shape}")
        logger.error("=" * 80)
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
    
    # Validate that the center point is within the mock polygon (it should always be for a circle)
    center_lng = float(lng)
    center_lat = float(lat)
    center_in_polygon = _point_in_polygon(center_lng, center_lat, coordinates)
    
    if not center_in_polygon:
        logger.warning(
            f"WARNING: Center point ({center_lat}, {center_lng}) is NOT within the mock isochrone polygon. "
            f"This should not happen for a circular polygon. Check coordinate calculations."
        )
    else:
        logger.debug(f"Mock polygon center validation: Center point is within polygon ✓")
    
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coordinates]  # Single ring polygon
        },
        "properties": {
            "minutes": minutes,
            "center": [center_lng, center_lat],
            "mock": True,
            "warnings": [] if center_in_polygon else ["Mock polygon does not enclose the center point (unexpected)."],
            "selection_reason": "mock_circle",
            "shell_label": "mock_circle"
        }
    }
    
    logger.info(f"Generated mock isochrone for {minutes} minutes at ({lat}, {lng}) with {len(coordinates)} points")
    logger.debug(f"Mock GeoJSON structure: type={geojson['type']}, geometry.type={geojson['geometry']['type']}, coordinates.rings={len(geojson['geometry']['coordinates'])}")
    return geojson
