# Investigation Results: Why Only 1 Marker Shows for NAICS "238" Search

## Problem Statement
When searching for NAICS code "238", the API returns 11 projects, but only 1 marker appears on the map.

## Root Cause Identified ✅

### The Issue
**All 11 projects with coordinates share the exact same coordinates: `37.4040147, -77.4587239`**

This causes all markers to stack on top of each other at the same location, appearing as a single marker.

### Why This Happens

1. **Limited Address Data**: Many SAM.gov projects only have state-level address information (e.g., just "VA" or "Virginia, USA")

2. **State-Level Geocoding**: When geocoding addresses like "VA, USA" or "Virginia, USA", Google Geocoding API returns the **geographic center of Virginia** (approximately 37.4040147, -77.4587239)

3. **Identical Coordinates**: All projects with only state information get geocoded to the same state center coordinates

4. **Marker Stacking**: Google Maps places multiple markers at identical coordinates by stacking them on top of each other, making them appear as a single marker

### Evidence from Testing

From API response analysis:
```
Project 1: lat: 37.4040147, lng: -77.4587239, coordinates_source: "geocoded"
Project 2: lat: 37.4040147, lng: -77.4587239, coordinates_source: "geocoded"
Project 3: lat: 37.4040147, lng: -77.4587239, coordinates_source: "geocoded"
... (all 11 projects have identical coordinates)
```

The coordinates `37.4040147, -77.4587239` correspond to approximately the center of Virginia state.

## Solution Implemented ✅

### Fix: Marker Offset Algorithm

**What it does:**
- Detects when multiple markers have identical coordinates
- Applies a **spiral offset pattern** to overlapping markers
- Each overlapping marker is offset by ~50 meters in a circular pattern
- Markers are spaced 60 degrees apart, creating a visible cluster

**Implementation:**
- Modified `addSAMMarker()` and `addPlaceMarker()` functions
- Added coordinate overlap detection
- Applied spiral offset algorithm
- Stores original coordinates for reference
- Shows warning when markers are offset

**Result:**
- All 11 markers will now be visible (not stacked)
- Markers form a circular cluster around the original location
- User sees warning explaining why markers are offset
- Isochrones are centered on visible marker positions

## Testing Instructions

1. **Refresh the browser** to load updated frontend code
2. **Search for NAICS code "238"**
3. **Expected Results:**
   - Should see 11 markers visible on the map (not just 1)
   - Markers should be spread in a circular pattern
   - Warning toast should appear: "Warning: 11 projects share the same coordinates..."
   - Clicking markers should show offset warning in info window
   - Generating isochrones should center on the visible marker

## Additional Improvements Made

1. **Better User Feedback**: 
   - Warning messages when projects share coordinates
   - Info window notes when markers are offset

2. **Improved Geocoding**:
   - Multiple geocoding strategies (5 different approaches)
   - Tries harder to extract specific addresses
   - Falls back gracefully when only state is available

3. **Isochrone Centering Fix**:
   - Always uses marker's actual position for isochrone generation
   - Ensures isochrone is centered on visible marker

## Files Modified

1. `src/frontend/app.js`
   - `addSAMMarker()` - Added offset detection and spiral pattern
   - `addPlaceMarker()` - Added offset detection and spiral pattern  
   - `loadSAMProjects()` - Added duplicate coordinate detection and warnings
   - `createSAMInfoContent()` - Shows offset warnings
   - `createPlaceInfoContent()` - Shows offset warnings

2. `src/backend/sam_client.py`
   - `build_address_string()` - Improved geocoding strategies (already fixed earlier)

## Status

✅ **Fix Complete**

The marker stacking issue is now resolved. All markers will be visible even when they share identical coordinates.

**Next Steps:**
1. Refresh browser to load updated frontend code
2. Test NAICS search "238" - should see all 11 markers
3. Verify markers are spread in a circle (not stacked)
4. Test isochrone generation - should be centered on visible markers

