"""
SAM.gov API client for fetching federal contract opportunities.
Uses SAM.gov v2 API endpoint with geocoding support.
Returns simplified, business-focused project objects.
"""
import json
import logging
import os
from collections import Counter
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Any
import requests
from config import SAM_BASE_URL, SAM_API_KEY, NAICS_CODES, STATE_FILTER
from geocode_client import geocode_address

logger = logging.getLogger(__name__)

LATITUDE_KEYS = {"lat", "latitude", "lat_deg", "latdeg", "y", "ycoord", "geo_lat", "center_lat"}
LONGITUDE_KEYS = {"lng", "lon", "long", "longitude", "long_deg", "longdeg", "x", "xcoord", "geo_lng", "center_lng"}


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_coordinates_in_structure(value: Any) -> Optional[Tuple[float, float]]:
    """
    Recursively search a nested SAM.gov structure for latitude/longitude pairs.
    """
    if isinstance(value, dict):
        lat = None
        lng = None
        for key, val in value.items():
            key_lower = key.lower()
            if key_lower in LATITUDE_KEYS and lat is None:
                lat = _coerce_float(val)
            elif key_lower in LONGITUDE_KEYS and lng is None:
                lng = _coerce_float(val)

        if lat is not None and lng is not None:
            return lat, lng

        for nested in value.values():
            coords = _find_coordinates_in_structure(nested)
            if coords:
                return coords

    elif isinstance(value, list):
        for item in value:
            coords = _find_coordinates_in_structure(item)
            if coords:
                return coords

    return None


def extract_coordinates_from_item(item: dict) -> Optional[Tuple[float, float]]:
    """
    Attempt to extract coordinates directly from SAM.gov payloads before geocoding.
    """
    if not isinstance(item, dict):
        return None

    possible_fields = [
        item.get("placeOfPerformance"),
        item.get("place_of_performance"),
        item.get("officeAddress"),
        item.get("office_address"),
        item.get("pointOfContact"),
        item.get("additionalPOCLocation"),
        item.get("location"),
    ]

    for field in possible_fields:
        if isinstance(field, str):
            # Strings (e.g., "VA") won't contain coordinates
            continue
        coords = _find_coordinates_in_structure(field)
        if coords:
            return coords

    # Fallback: search entire item
    return _find_coordinates_in_structure(item)


def extract_location_fields(item: dict) -> Dict[str, Optional[str]]:
    """
    Extract city, state, zipcode, countryCode from either placeOfPerformance
    (preferred) or officeAddress.

    Args:
        item: Raw SAM.gov opportunity dictionary

    Returns:
        Dictionary with city, state, zipcode, country fields
    """
    # Try placeOfPerformance first (most accurate for project location)
    pop = item.get("placeOfPerformance")

    # SAM.gov might return placeOfPerformance as a string ("VA") instead of object
    # If it's a string, it's just the state code - we need to get address from elsewhere
    if isinstance(pop, str):
        logger.debug(f"placeOfPerformance is string: '{pop}' - trying officeAddress")
        pop = item.get("officeAddress")

    # Fallback to officeAddress if placeOfPerformance is missing
    if not pop or (isinstance(pop, dict) and not any(pop.values())):
        pop = item.get("officeAddress")

    # If still nothing, try alternative field names
    if not pop or (isinstance(pop, dict) and not any(pop.values())):
        pop = item.get("pointOfContact", {})

    addr = pop or {}

    # Additional safety: if addr is a string, convert to empty dict
    if not isinstance(addr, dict):
        logger.debug(f"Address field is not a dict (type: {type(addr)}): {addr}")
        addr = {}

    city = None
    state = None
    zipcode = None
    country = None

    # Extract city - handle both dict and string formats
    city_field = addr.get("city")
    if isinstance(city_field, dict):
        city = city_field.get("name") or city_field.get("code")
    elif isinstance(city_field, str):
        city = city_field.strip() if city_field.strip() else None

    # Extract state - handle both dict and string formats
    state_field = addr.get("state")
    if isinstance(state_field, dict):
        state = state_field.get("code") or state_field.get("name")
    elif isinstance(state_field, str):
        state = state_field.strip() if state_field.strip() else None

    # Extract zipcode - try multiple field names
    zipcode = addr.get("zip") or addr.get("zipcode") or addr.get("zipCode")
    if zipcode and isinstance(zipcode, str):
        zipcode = zipcode.strip()

    # Extract country - handle both dict and string formats
    country_field = addr.get("country")
    if isinstance(country_field, dict):
        country = country_field.get("code") or country_field.get("name")
    elif isinstance(country_field, str):
        country = country_field.strip() if country_field.strip() else None

    # Fallback to countryCode field
    if not country:
        country = addr.get("countryCode")

    return {
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "country": country,
    }


def build_address_string(item: dict) -> Optional[str]:
    """
    Build a freeform address string from location fields for geocoding.
    ALWAYS tries to geocode if ANY location data is available (city, state, zipcode).
    Prioritizes more specific addresses but falls back to less specific ones.
    Goal: Always provide coordinates for TravelTime API, even if city-level or state-level.

    Args:
        item: Raw SAM.gov opportunity dictionary

    Returns:
        Freeform address string or None (only if absolutely no location data)
    """
    loc = extract_location_fields(item)

    # Strategy 1: Check for full address strings in raw data FIRST (most specific)
    # Some SAM.gov records have formatted addresses in other fields
    # This might contain actual street addresses or more complete location info
    if isinstance(item, dict):
        address_fields = [
            item.get("fullAddress"),
            item.get("full_address"),
            item.get("address"),
            item.get("locationString"),
            item.get("location_string"),
        ]
        for addr_field in address_fields:
            if addr_field and isinstance(addr_field, str) and addr_field.strip():
                addr_clean = addr_field.strip()
                # If it looks like an address (contains state, zipcode, or street-like patterns), use it
                addr_lower = addr_clean.lower()
                has_state = any(state_code in addr_lower for state_code in ["va", "virginia", "va "])
                has_zip = any(char.isdigit() for char in addr_clean[-5:])
                has_street = any(word in addr_lower for word in ["street", "st", "avenue", "ave", "road", "rd", "drive", "dr", "lane", "ln"])
                
                if has_state or has_zip or has_street:
                    logger.debug(f"Found full address string in raw data: '{addr_clean[:80]}'")
                    return addr_clean

    # Strategy 2: City + State + ZIPCODE (most specific combination)
    # This will geocode to a specific area within the city (best for TravelTime API)
    if loc.get("city") and loc.get("state") and loc.get("zipcode"):
        address = f"{loc['city']}, {loc['state']} {loc['zipcode']}"
        logger.debug(f"Geocoding with city+state+zip: '{address}'")
        return address

    # Strategy 3: City + State (city-level coordinates - good for TravelTime API)
    # This will geocode to city center, which is acceptable for travel time calculations
    if loc.get("city") and loc.get("state"):
        address = f"{loc['city']}, {loc['state']}"
        logger.debug(f"Geocoding with city+state: '{address}' (city-level coordinates)")
        return address

    # Strategy 4: City alone (if we have city but no state, still try to geocode)
    # Google can often geocode city names, especially well-known cities
    if loc.get("city"):
        city = str(loc["city"]).strip()
        logger.debug(f"Geocoding city only: '{city}' (no state available)")
        return city

    # Strategy 5: State + ZIPCODE (zipcode-level coordinates)
    # ZIP codes can be geocoded to a general area
    if loc.get("zipcode") and loc.get("state"):
        address = f"{loc['state']} {loc['zipcode']}"
        logger.debug(f"Geocoding with state+zip: '{address}' (zipcode-level coordinates)")
        return address

    # Strategy 6: State only (state-level coordinates - least specific but still usable)
    # This will geocode to state center, which is acceptable for TravelTime API
    # Better than nothing - at least provides coordinates
    if loc.get("state"):
        state = str(loc["state"]).strip()
        address = f"{state}, USA"
        logger.debug(f"Geocoding state only: '{address}' (state-level coordinates - less precise but usable)")
        return address

    # Strategy 7: ZIPCODE alone (if we somehow have zipcode but no state)
    if loc.get("zipcode"):
        zipcode = str(loc["zipcode"]).strip()
        logger.debug(f"Geocoding zipcode only: '{zipcode}' (no state available)")
        return zipcode

    # Only return None if we have absolutely no location data
    # This should be rare - most SAM.gov records have at least state information
    logger.warning("No location data available for geocoding")
    return None


def normalize_sam_opportunity(item: dict) -> dict:
    """
    Convert a raw SAM.gov opportunity dict into a simplified, business-facing structure.

    Args:
        item: Raw SAM.gov opportunity dictionary

    Returns:
        Normalized project dictionary with business-focused fields
    """
    try:
        location = extract_location_fields(item)
        address = build_address_string(item)
    except Exception as e:
        logger.error(f"Error extracting location from SAM item: {e}")
        logger.error(f"Item keys: {list(item.keys()) if isinstance(item, dict) else 'NOT A DICT'}")
        # Return minimal data with no coordinates
        return {
            "id": item.get("noticeId"),
            "title": item.get("title"),
            "posted_date": item.get("postedDate"),
            "response_deadline": item.get("responseDeadLine"),
            "naics": item.get("naicsCode"),
            "project_type": item.get("type"),
            "department": item.get("department") or item.get("fullParentPathName"),
            "city": None,
            "state": None,
            "zipcode": None,
            "country": None,
            "address": None,
            "lat": None,
            "lng": None,
            "coordinates_source": "none",
            "estimated_award_amount": None,
            "ui_link": item.get("uiLink"),
        }

    coordinates_source = "none"
    lat = None
    lng = None
    notice_id = item.get('noticeId', 'UNKNOWN')
    title = item.get('title', 'N/A')[:50]

    sam_coordinates = extract_coordinates_from_item(item)
    if sam_coordinates:
        lat_candidate, lng_candidate = sam_coordinates
        if lat_candidate is not None and lng_candidate is not None:
            lat = float(lat_candidate)
            lng = float(lng_candidate)
            coordinates_source = "sam"
            logger.info(f"[{notice_id}] Using SAM-provided coordinates ({lat:.4f}, {lng:.4f})")

    if address:
        if coordinates_source == "sam":
            logger.debug(f"[{notice_id}] Skipping geocode lookup (coordinates already provided by SAM.gov)")
        else:
            logger.info(f"[{notice_id}] Geocoding: '{address}'")
            lat_candidate, lng_candidate = geocode_address(address)
            if lat_candidate and lng_candidate:
                lat = lat_candidate
                lng = lng_candidate
                coordinates_source = "geocoded"
                logger.info(f"[{notice_id}] Geocode success: ({lat:.4f}, {lng:.4f})")
            else:
                logger.error(f"[{notice_id}] GEOCODE FAILED")
                logger.error(f"  Title: {title}")
                logger.error(f"  Address: {address}")
                logger.error(f"  Location fields: {location}")
                # Safely log raw data with str() to prevent encoding issues
                try:
                    logger.error(f"  Raw placeOfPerformance: {str(item.get('placeOfPerformance'))[:200]}")
                    logger.error(f"  Raw officeAddress: {str(item.get('officeAddress'))[:200]}")
                except Exception:
                    logger.error("  (Could not log raw location data)")
    else:
        if coordinates_source == "none":
            logger.error(f"[{notice_id}] NO ADDRESS - Cannot geocode")
            logger.error(f"  Title: {title}")
            logger.error(f"  Location fields: {location}")
            # Safely log raw data
            try:
                logger.error(f"  Raw placeOfPerformance: {str(item.get('placeOfPerformance'))[:200]}")
                logger.error(f"  Raw officeAddress: {str(item.get('officeAddress'))[:200]}")
            except Exception:
                logger.error("  (Could not log raw location data)")
    
    # award.amount may be missing or a string; try to convert to float
    award_info = item.get("award") or {}
    amount_raw = award_info.get("amount")
    try:
        estimated_award_amount = float(amount_raw.replace(",", "")) if amount_raw is not None else None
    except Exception:
        estimated_award_amount = None
    
    return {
        "id": item.get("noticeId"),
        "title": item.get("title"),
        "posted_date": item.get("postedDate"),
        "response_deadline": item.get("responseDeadLine"),
        "naics": item.get("naicsCode"),
        "project_type": item.get("type"),  # e.g. "Award Notice"
        "department": item.get("department") or item.get("fullParentPathName"),
        "city": location.get("city"),
        "state": location.get("state"),
        "zipcode": location.get("zipcode"),
        "country": location.get("country"),
        "address": address,
        "lat": lat,
        "lng": lng,
        "estimated_award_amount": estimated_award_amount,
        "coordinates_source": coordinates_source,
        "ui_link": item.get("uiLink"),
    }


def fetch_live_projects(
    posted_from: date,
    posted_to: date,
    limit: int = 50,
    keyword: Optional[str] = None,
    naics_code: Optional[str] = None,
    ptype: Optional[str] = None,
) -> List[dict]:
    """
    Call the SAM.gov opportunities/v2/search endpoint and return a list of
    normalized project dicts for business users.
    
    Args:
        posted_from: Start date for opportunity search
        posted_to: End date for opportunity search
        limit: Maximum number of results to return
        keyword: Optional keyword search query (uses "Keyword Search" parameter)
        naics_code: Optional NAICS code to filter by (e.g., "327300", "238110")
        ptype: Optional project type filter (e.g., "a" for Award Notice)
        
    Returns:
        List of normalized project dictionaries
        
    Raises:
        RuntimeError: If SAM_API_KEY is not configured
    """
    if not SAM_API_KEY:
        raise RuntimeError("SAM_API_KEY is not configured; cannot call SAM.gov live.")
    
    params = {
        "limit": limit,
        "api_key": SAM_API_KEY,
        "postedFrom": posted_from.strftime("%m/%d/%Y"),
        "postedTo": posted_to.strftime("%m/%d/%Y"),
    }
    
    if keyword:
        params["q"] = keyword  # Keyword search - "q" is the standard parameter for SAM.gov v2
    if naics_code:
        # SAM.gov API uses "naicsCode" parameter
        # Ensure it's properly formatted (strip whitespace)
        naics_clean = str(naics_code).strip()
        params["naicsCode"] = naics_clean
        logger.debug(f"Adding NAICS code filter: {naics_clean}")
    if ptype:
        params["ptype"] = ptype  # e.g., "a" for Award Notice
    
    # State filtering is handled via post-processing (see filtering logic below)
    # The SAM.gov API v2 does not reliably support state filtering via query parameters
    # Attempting to add placeOfPerformance.stateCode causes 500 errors
    # State filtering happens after receiving results (lines 465-473)
    if STATE_FILTER:
        logger.debug(f"State filter '{STATE_FILTER}' will be applied via post-processing after API response")
    
    logger.info("Calling SAM.gov with params: %s", params)
    
    try:
        resp = requests.get(SAM_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        # Check if the error message contains rate limiting info
        error_text = str(e)
        response_text = e.response.text if e.response else ""
        
        if status_code == 429 or "429" in error_text or "Too Many Requests" in error_text or "Too Many Requests" in response_text:
            logger.error("SAM.gov API rate limit exceeded (429)")
            logger.error("You've made too many requests. Please wait a few minutes and try again.")
            raise RuntimeError("SAM.gov API rate limit exceeded. Please wait a few minutes and try again.") from e
        elif status_code == 500:
            # 500 errors often indicate invalid parameters
            logger.error(f"SAM.gov API returned 500 Internal Server Error")
            logger.error(f"Request parameters: {params}")
            logger.error(f"This may indicate invalid parameter names or values")
            logger.error(f"Response: {response_text[:500]}")
            raise RuntimeError(
                f"SAM.gov API returned 500 error. This may indicate invalid parameters. "
                f"Check that NAICS code '{naics_code if naics_code else 'N/A'}' is valid and properly formatted."
            ) from e
        else:
            logger.error(f"HTTP error calling SAM.gov API: {status_code} - {e}")
            if e.response:
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    except requests.exceptions.RequestException as e:
        logger.error("Network error calling SAM.gov API: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error calling SAM.gov API: %s", e)
        raise
    
    raw_items = data.get("opportunitiesData", []) or []

    # DEBUG: Log structure of first item to understand SAM.gov format
    if raw_items and len(raw_items) > 0:
        first_item = raw_items[0]
        logger.debug("=" * 60)
        logger.debug("SAMPLE SAM.GOV ITEM STRUCTURE (first result):")
        logger.debug(f"  Keys: {list(first_item.keys())}")
        if "placeOfPerformance" in first_item:
            pop = first_item.get("placeOfPerformance")
            logger.debug(f"  placeOfPerformance type: {type(pop)}")
            if isinstance(pop, dict):
                logger.debug(f"  placeOfPerformance keys: {list(pop.keys())}")
                logger.debug(f"  placeOfPerformance content: {pop}")
        if "officeAddress" in first_item:
            addr = first_item.get("officeAddress")
            logger.debug(f"  officeAddress type: {type(addr)}")
            if isinstance(addr, dict):
                logger.debug(f"  officeAddress keys: {list(addr.keys())}")
        logger.debug("=" * 60)

    projects = []
    filtered_counts = {
        "inactive": 0,
        "non_usa": 0,
        "wrong_state": 0,
        "accepted": 0
    }

    for item in raw_items:
        try:
            # Only keep active records in the USA
            if item.get("active") != "Yes":
                filtered_counts["inactive"] += 1
                continue

            loc = extract_location_fields(item)
            if loc.get("country") not in (None, "USA"):
                filtered_counts["non_usa"] += 1
                continue

            # Filter by Virginia state if state is available
            # Handle variations: VA, Virginia, va, virginia
            state = loc.get("state")
            if state:
                state_upper = str(state).upper().strip()
                # Accept "VA" or "VIRGINIA"
                if state_upper not in ("VA", "VIRGINIA"):
                    filtered_counts["wrong_state"] += 1
                    continue

            # No longer filtering by NAICS codes - keyword search is handled by SAM.gov API "Keyword Search" parameter
            normalized = normalize_sam_opportunity(item)
            projects.append(normalized)
            filtered_counts["accepted"] += 1
        except Exception as e:
            # If processing a single item fails, log it but continue with other items
            notice_id = item.get("noticeId", "UNKNOWN")
            logger.error(f"Error processing SAM.gov item {notice_id}: {e}")
            logger.debug(f"  Item keys: {list(item.keys()) if isinstance(item, dict) else 'NOT A DICT'}")
            # Continue processing other items instead of crashing
            continue

    logger.info(f"SAM.gov filtering results: {len(raw_items)} total → {filtered_counts['accepted']} accepted")
    logger.info(f"  Filtered out: {filtered_counts['inactive']} inactive, {filtered_counts['non_usa']} non-USA, {filtered_counts['wrong_state']} wrong state")

    # Count how many have valid coordinates
    with_coords = sum(1 for p in projects if p.get("lat") and p.get("lng"))
    without_coords = len(projects) - with_coords
    logger.info(f"  Geocoding results: {with_coords} with coordinates, {without_coords} without coordinates")
    if projects:
        source_counts = Counter(p.get("coordinates_source", "unknown") for p in projects)
        logger.info("  Coordinate sources: %s", ", ".join(f"{src}: {cnt}" for src, cnt in source_counts.items()))

    if without_coords > 0:
        logger.warning(f"  ⚠ {without_coords} projects will NOT appear on map (missing coordinates)")

    return projects


def fetch_projects(mock: bool = False) -> List[Dict]:
    """
    Fetch SAM.gov opportunities (backward compatibility wrapper).
    
    Args:
        mock: If True, load from sample_sam.json instead of API
        
    Returns:
        List of project dictionaries
    """
    if mock:
        return _load_mock_data()
    
    # For live mode, use default date range (last 90 days)
    today = date.today()
    posted_to = today
    posted_from = today - timedelta(days=90)
    
    try:
        return fetch_live_projects(
            posted_from=posted_from,
            posted_to=posted_to,
            limit=50,
            ptype="a"
        )
    except RuntimeError as e:
        logger.warning("%s. Falling back to mock data.", str(e))
        return _load_mock_data()
    except Exception as e:
        logger.error("Error fetching live projects: %s. Falling back to mock data.", e)
        return _load_mock_data()


def _load_mock_data() -> List[Dict]:
    """
    Load mock SAM.gov data from sample_sam.json.
    All mock data should be in Virginia and match required NAICS codes.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "sample_sam.json")
        
        if not os.path.exists(json_path):
            logger.warning("sample_sam.json not found, returning empty list")
            return []
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Validate mock data structure
        if not isinstance(data, list):
            logger.error("sample_sam.json should contain a list of projects")
            return []
        
        # Filter to ensure all entries match our NAICS codes
        filtered_data = []
        for project in data:
            if project.get("naics") in NAICS_CODES:
                # Validate coordinates are in Virginia
                lat = project.get("lat")
                lng = project.get("lng")
                if lat and lng and _is_virginia_location(lat, lng):
                    project = project.copy()
                    project.setdefault("coordinates_source", project.get("coordinates_source", "mock"))
                    filtered_data.append(project)
        
        logger.info(f"Loaded {len(filtered_data)} mock SAM.gov projects (filtered by NAICS and Virginia)")
        return filtered_data
        
    except FileNotFoundError:
        logger.warning("sample_sam.json not found, returning empty list")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing sample_sam.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading mock data: {e}")
        return []


def _is_virginia_location(lat: float, lng: float) -> bool:
    """
    Check if coordinates are within Virginia state boundaries.
    Virginia approximate bounds: 36.5-39.5 N, 83.5-75.0 W
    """
    if not lat or not lng:
        return False
    
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return False
    
    # Virginia approximate boundaries
    # More precise bounds: 36.5407° N to 39.4660° N, 83.6754° W to 75.2423° W
    va_lat_min, va_lat_max = 36.5, 39.5
    va_lng_min, va_lng_max = -83.5, -75.0
    
    return (va_lat_min <= lat <= va_lat_max and 
            va_lng_min <= lng <= va_lng_max)
