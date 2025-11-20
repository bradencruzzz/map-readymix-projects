"""
Debug script to test isochrone generation and coordinate handling
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'backend'))

from iso_client import get_isochrone

# Test with Richmond, VA coordinates
test_lat, test_lng = 37.5407, -77.4360
print(f"Testing isochrone generation for Richmond, VA")
print(f"Input coordinates: lat={test_lat}, lng={test_lng}")
print("=" * 60)

try:
    result = get_isochrone(test_lat, test_lng, 30, mock=False)

    print(f"\nResult type: {result.get('type')}")
    print(f"Geometry type: {result.get('geometry', {}).get('type')}")
    print(f"Is mock: {result.get('properties', {}).get('mock')}")

    coords = result['geometry']['coordinates'][0]
    print(f"\nTotal coordinates: {len(coords)}")
    print(f"\nFirst 3 coordinates:")
    for i, coord in enumerate(coords[:3]):
        print(f"  [{i}]: {coord} (type: {type(coord)})")
        if isinstance(coord, list):
            print(f"       -> lng={coord[0]}, lat={coord[1]}")

    print(f"\nLast coordinate: {coords[-1]}")

    # Calculate bounds
    if coords and isinstance(coords[0], list):
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        print(f"\nCoordinate bounds:")
        print(f"  Longitude: {min(lngs):.6f} to {max(lngs):.6f}")
        print(f"  Latitude: {min(lats):.6f} to {max(lats):.6f}")

        # Check if bounds are reasonable for Virginia
        va_lng_range = (-83.5, -75.0)
        va_lat_range = (36.5, 39.5)

        lng_in_va = va_lng_range[0] <= min(lngs) and max(lngs) <= va_lng_range[1]
        lat_in_va = va_lat_range[0] <= min(lats) and max(lats) <= va_lat_range[1]

        print(f"\n  Longitude in VA range: {lng_in_va}")
        print(f"  Latitude in VA range: {lat_in_va}")

        if not lng_in_va or not lat_in_va:
            print(f"\n  WARNING: Coordinates appear to be outside Virginia!")
            print(f"  This suggests the isochrone might not display correctly")

    # Show full GeoJSON structure
    print(f"\n=== Full GeoJSON (first 500 chars) ===")
    json_str = json.dumps(result, indent=2)
    print(json_str[:500])
    print("...")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
