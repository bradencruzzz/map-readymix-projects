# Isochrone Centering Fix - Complete

## Problem
Isochrones were not centered on the requested location. The center marker appeared outside the polygon bounds, with offsets up to 17-20 km.

## Root Cause
The TravelTime API returns **multiple shapes** (up to 8 in our tests) representing disconnected regions that can be reached within the drive time. Our backend was only checking the **first shape**, which often didn't contain the requested center point.

For example, when requesting an isochrone for "5700 Lake Wright Dr, Norfolk, VA":
- **Shape 0** (first shape): 396 coordinates, bounds did NOT include center point
- **Shape 5** (correct shape): 1,669 coordinates, bounds DID include center point

## Solution
Updated `src/backend/iso_client.py` to:
1. **Check ALL shapes** returned by the TravelTime API (not just the first one)
2. **Select the shape that contains the center point** using:
   - First priority: Point-in-polygon test
   - Second priority: Bounding box containment
   - Fallback: Largest shape by coordinate count

## Changes Made

### 1. Updated API Request Structure (`src/backend/iso_client.py`)
Changed from `departure_searches` to `arrival_searches` to match the working Cloudflare Worker implementation:
```python
body = {
    "arrival_searches": [
        {
            "id": f"isochrone_{minutes}min_{lat:.5f}_{lng:.5f}",
            "coords": {"lat": float(lat), "lng": float(lng)},
            "arrival_time": arrival_time_iso,
            "travel_time": int(minutes * 60),
            "transportation": {"type": "driving"}
        }
    ]
}
```

### 2. Multi-Shape Selection (`src/backend/iso_client.py`)
**Before:**
```python
first_shape = shapes[0]  # Only checked first shape
```

**After:**
```python
for shape_idx, shape in enumerate(shapes):
    # Check all shapes and add to candidates
    if "shell" in shape:
        candidate_shells.append((f"shape[{shape_idx}].shell", shape.get("shell", [])))
```

### 3. Enhanced Geocoding Logging (`src/backend/sam_client.py`)
Added precision level detection for geocoding:
- `_get_geocoding_precision_level()` function
- Logs show whether coordinates are street-level, city-level, or state-level
- Helps verify coordinates have sufficient detail for TravelTime API

## Test Results

### Before Fix:
- Coordinate count: 396
- Center: `lng=-76.207741, lat=36.879877`
- Polygon bounds: `lng [-76.495316, -76.282830], lat [36.963177, 37.122005]`
- **Center OUTSIDE polygon** ❌

### After Fix:
- Coordinate count: 1,669
- Center: `lng=-76.207741, lat=36.879877`
- Polygon bounds: `lng [-76.573494, -75.965640], lat [36.559690, 36.969036]`
- **Center INSIDE polygon** ✅

## Files Modified
1. `src/backend/iso_client.py` - Multi-shape checking and arrival_searches API structure
2. `src/backend/sam_client.py` - Enhanced geocoding precision logging

## Testing
Tested with Playwright MCP on location "5700 Lake Wright Dr, Norfolk, VA 23502":
- ✅ Isochrone generates successfully
- ✅ Polygon contains center point
- ✅ No offset warnings
- ✅ 1,669 coordinates returned (correct shape selected)

## Notes
- The TravelTime API can return multiple disconnected shapes for complex road networks
- Always check ALL shapes, not just the first one
- The `arrival_searches` vs `departure_searches` difference didn't affect centering, but aligns with best practices
- Some locations may still show minor offsets due to road snapping, but major 17-20 km offsets are now fixed

## Next Steps
1. Monitor isochrone generation for other locations to ensure fix works consistently
2. Consider adding user-facing messaging when multiple shapes are available
3. Document expected behavior when TravelTime returns multiple disconnected regions

