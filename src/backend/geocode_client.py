"""
Google Geocoding API client for converting addresses to coordinates.
"""
from typing import Optional, Tuple
from collections import OrderedDict
import requests
import logging
from config import GOOGLE_MAPS_API_KEY, GOOGLE_GEOCODE_URL

logger = logging.getLogger(__name__)

MAX_GEOCODE_CACHE_SIZE = 512
_geocode_cache: "OrderedDict[str, Tuple[Optional[float], Optional[float]]]" = OrderedDict()


def geocode_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Use Google Geocoding to turn a freeform address string into (lat, lng).
    Includes an in-memory LRU cache to avoid repeated lookups for the same address.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not set; cannot geocode addresses!")
        return None, None
    
    if not address or not address.strip():
        logger.warning("Empty address provided for geocoding")
        return None, None
    
    normalized_address = " ".join(address.strip().split())
    
    if normalized_address in _geocode_cache:
        _geocode_cache.move_to_end(normalized_address)
        logger.debug(f"[Geocode] Cache hit for '{normalized_address}'")
        return _geocode_cache[normalized_address]
    
    lat_lng = _call_google_geocode(normalized_address)
    if lat_lng != (None, None):
        _remember_geocode(normalized_address, lat_lng)
    return lat_lng


def _remember_geocode(address: str, lat_lng: Tuple[Optional[float], Optional[float]]) -> None:
    _geocode_cache[address] = lat_lng
    _geocode_cache.move_to_end(address)
    if len(_geocode_cache) > MAX_GEOCODE_CACHE_SIZE:
        evicted_key, _ = _geocode_cache.popitem(last=False)
        logger.debug(f"[Geocode] Cache evicted oldest entry '{evicted_key}'")


def _call_google_geocode(address: str) -> Tuple[Optional[float], Optional[float]]:
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
    }
    
    try:
        resp = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        logger.error(f"Network error calling Google Geocoding API: {exc}")
        logger.error(f"  Address attempted: '{address}'")
        return None, None
    except Exception as exc:
        logger.error(f"Unexpected error calling Google Geocoding: {exc}")
        logger.error(f"  Address attempted: '{address}'")
        return None, None
    
    status = data.get("status")
    if status != "OK":
        logger.warning(f"Google Geocoding returned status: {status} for address: '{address}'")
        if status == "ZERO_RESULTS":
            logger.warning("  → Google couldn't find this address")
        elif status == "REQUEST_DENIED":
            logger.error("  → API request denied! Check your GOOGLE_MAPS_API_KEY")
            logger.error(f"  → Error message: {data.get('error_message', 'No error message')}")
        elif status == "INVALID_REQUEST":
            logger.error(f"  → Invalid request. Address: '{address}'")
        elif status == "OVER_QUERY_LIMIT":
            logger.error("  → Google API quota exceeded!")
        return None, None
    
    if not data.get("results"):
        logger.warning(f"No results in geocoding response for address: '{address}'")
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
    except (KeyError, ValueError, TypeError) as exc:
        logger.error("Error parsing geocoding response: %s", exc)
        return None, None

