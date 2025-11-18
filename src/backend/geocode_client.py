"""
Google Geocoding API client for converting addresses to coordinates.
"""
from typing import Optional, Tuple
import requests
import logging
from config import GOOGLE_MAPS_API_KEY, GOOGLE_GEOCODE_URL

logger = logging.getLogger(__name__)


def geocode_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Use Google Geocoding to turn a freeform address string into (lat, lng).
    
    Args:
        address: Freeform address string (e.g., "Richmond, VA, 23219, USA")
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if geocoding fails
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set; skipping geocoding.")
        return None, None
    
    if not address or not address.strip():
        logger.warning("Empty address provided for geocoding")
        return None, None
    
    params = {
        "address": address.strip(),
        "key": GOOGLE_MAPS_API_KEY,
    }
    
    try:
        resp = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("Error calling Google Geocoding: %s", exc)
        return None, None
    
    if data.get("status") != "OK" or not data.get("results"):
        logger.warning("No geocoding results for address: %s", address)
        return None, None
    
    try:
        loc = data["results"][0]["geometry"]["location"]
        lat = loc.get("lat")
        lng = loc.get("lng")
        
        if lat is not None and lng is not None:
            return float(lat), float(lng)
        else:
            logger.warning("Invalid coordinates in geocoding response for address: %s", address)
            return None, None
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Error parsing geocoding response: %s", e)
        return None, None

