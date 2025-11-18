"""
SAM.gov API client for fetching federal contract opportunities.
Uses SAM.gov v2 API endpoint with geocoding support.
Returns simplified, business-focused project objects.
"""
import json
import logging
import os
from datetime import date, timedelta
from typing import List, Dict, Optional
import requests
from config import SAM_BASE_URL, SAM_API_KEY, NAICS_CODES, STATE_FILTER
from geocode_client import geocode_address

logger = logging.getLogger(__name__)


def extract_location_fields(item: dict) -> Dict[str, Optional[str]]:
    """
    Extract city, state, zipcode, countryCode from either placeOfPerformance
    (preferred) or officeAddress.
    
    Args:
        item: Raw SAM.gov opportunity dictionary
        
    Returns:
        Dictionary with city, state, zipcode, country fields
    """
    pop = item.get("placeOfPerformance") or {}
    addr = pop or item.get("officeAddress") or {}
    
    city = None
    state = None
    zipcode = None
    country = None
    
    city_field = addr.get("city")
    if isinstance(city_field, dict):
        city = city_field.get("name")
    else:
        city = city_field
    
    state_field = addr.get("state")
    if isinstance(state_field, dict):
        state = state_field.get("code")
    else:
        state = state_field
    
    zipcode = addr.get("zip") or addr.get("zipcode")
    country_field = addr.get("country") or {}
    if isinstance(country_field, dict):
        country = country_field.get("code")
    else:
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
    
    Args:
        item: Raw SAM.gov opportunity dictionary
        
    Returns:
        Freeform address string or None
    """
    loc = extract_location_fields(item)
    parts = [
        loc.get("city"),
        loc.get("state"),
        loc.get("zipcode"),
        loc.get("country"),
    ]
    # For simplicity, we ignore streetAddress for now; can be added if needed.
    address = ", ".join(p for p in parts if p)
    return address or None


def normalize_sam_opportunity(item: dict) -> dict:
    """
    Convert a raw SAM.gov opportunity dict into a simplified, business-facing structure.
    
    Args:
        item: Raw SAM.gov opportunity dictionary
        
    Returns:
        Normalized project dictionary with business-focused fields
    """
    location = extract_location_fields(item)
    address = build_address_string(item)
    
    lat = None
    lng = None
    if address:
        lat, lng = geocode_address(address)
    
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
        "ui_link": item.get("uiLink"),
    }


def fetch_live_projects(
    posted_from: date,
    posted_to: date,
    limit: int = 50,
    title: Optional[str] = None,
    ptype: Optional[str] = None,
) -> List[dict]:
    """
    Call the SAM.gov opportunities/v2/search endpoint and return a list of
    normalized project dicts for business users.
    
    Args:
        posted_from: Start date for opportunity search
        posted_to: End date for opportunity search
        limit: Maximum number of results to return
        title: Optional title filter
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
    
    if title:
        params["title"] = title
    if ptype:
        params["ptype"] = ptype  # e.g., "a" for Award Notice
    
    logger.info("Calling SAM.gov with params: %s", params)
    
    try:
        resp = requests.get(SAM_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error calling SAM.gov API: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error calling SAM.gov API: %s", e)
        raise
    
    raw_items = data.get("opportunitiesData", []) or []
    
    projects = []
    for item in raw_items:
        # Only keep active records in the USA
        if item.get("active") != "Yes":
            continue
        
        loc = extract_location_fields(item)
        if loc.get("country") not in (None, "USA"):
            continue
        
        # Filter by Virginia state if state is available
        if loc.get("state") and loc.get("state") != STATE_FILTER:
            continue
        
        # Filter by NAICS codes if naicsCode is available
        naics_code = item.get("naicsCode")
        if naics_code and naics_code not in NAICS_CODES:
            continue
        
        normalized = normalize_sam_opportunity(item)
        projects.append(normalized)
    
    logger.info("Fetched %d projects from SAM.gov (filtered by active, USA, VA, NAICS)", len(projects))
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
