"""
Quick diagnostic script to test geocoding and API connectivity.
Run this to verify your API keys are working correctly.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'backend'))

from config import GOOGLE_MAPS_API_KEY, SAM_API_KEY, TRAVELTIME_API_KEY, TRAVELTIME_APP_ID
from geocode_client import geocode_address
from iso_client import get_isochrone

print("=" * 60)
print("SiteScoutLite Diagnostic Test")
print("=" * 60)

# Check API keys
print("\n1. Checking API Keys...")
print(f"   GOOGLE_MAPS_API_KEY: {'[SET]' if GOOGLE_MAPS_API_KEY else '[MISSING]'}")
print(f"   SAM_API_KEY: {'[SET]' if SAM_API_KEY else '[MISSING]'}")
print(f"   TRAVELTIME_API_KEY: {'[SET]' if TRAVELTIME_API_KEY else '[MISSING]'}")
print(f"   TRAVELTIME_APP_ID: {'[SET]' if TRAVELTIME_APP_ID else '[MISSING]'}")

# Test geocoding
print("\n2. Testing Google Geocoding API...")
if GOOGLE_MAPS_API_KEY:
    test_address = "Richmond, VA, 23219"
    print(f"   Testing address: '{test_address}'")
    lat, lng = geocode_address(test_address)
    if lat and lng:
        print(f"   [SUCCESS] Geocoding: ({lat}, {lng})")
    else:
        print(f"   [FAILED] Geocoding - check logs above for details")
else:
    print("   [SKIPPED] API key not set")

# Test isochrone
print("\n3. Testing TravelTime Isochrone API...")
if TRAVELTIME_API_KEY and TRAVELTIME_APP_ID:
    test_lat, test_lng = 37.5407, -77.4360  # Richmond, VA
    print(f"   Testing location: ({test_lat}, {test_lng})")
    try:
        result = get_isochrone(test_lat, test_lng, 30, mock=False)
        if result and result.get("geometry"):
            coords = result["geometry"]["coordinates"]
            print(f"   [SUCCESS] Isochrone: {len(coords[0])} coordinates")
            print(f"   Mock mode: {result.get('properties', {}).get('mock', False)}")
        else:
            print(f"   [FAILED] Isochrone - no geometry returned")
    except Exception as e:
        print(f"   [FAILED] Isochrone: {e}")
else:
    print("   [SKIPPED] API credentials not set")
    print("   Testing mock fallback...")
    try:
        result = get_isochrone(37.5407, -77.4360, 30, mock=True)
        if result and result.get("geometry"):
            coords = result["geometry"]["coordinates"]
            print(f"   [SUCCESS] Mock isochrone: {len(coords[0])} coordinates")
        else:
            print(f"   [FAILED] Mock isochrone")
    except Exception as e:
        print(f"   [FAILED] Mock isochrone error: {e}")

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)
print("\nIf any tests failed, check the error messages above.")
print("Make sure your .env file contains all required API keys.")
