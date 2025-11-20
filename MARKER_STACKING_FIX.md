# Marker Stacking Issue - Root Cause & Fix

## Problem Identified

When searching for NAICS code "238", the API returns 11 projects, but only **1 marker appears** on the map (or all markers appear stacked on top of each other).

## Root Cause Analysis

### The Issue
All 11 projects that have coordinates share the **exact same coordinates**: `37.4040147, -77.4587239`

### Why This Happens
1. Many SAM.gov projects only have **state-level address information** (e.g., just "VA" or "Virginia")
2. When geocoding state-only addresses like "VA, USA", Google Geocoding API returns the **state center** location
3. All projects with only state information get geocoded to the same state center coordinates
4. When Google Maps places multiple markers at identical coordinates, they **stack on top of each other**, appearing as a single marker

### Evidence
From API response testing:
- 11 projects returned with coordinates
- All 11 have identical coordinates: `lat: 37.4040147, lng: -77.4587239`
- All have `coordinates_source: "geocoded"` (not from SAM.gov directly)
- This location (37.4040147, -77.4587239) is approximately the center of Virginia

## Solution Implemented

### Fix #1: Marker Offset Algorithm ✅
**File:** `src/frontend/app.js` - `addSAMMarker()` and `addPlaceMarker()` functions

**What it does:**
- Detects when multiple markers have identical coordinates (within 0.0001 degrees)
- Applies a **spiral offset pattern** to overlapping markers
- Each overlapping marker is offset by ~50 meters in a circular pattern
- Markers are spaced 60 degrees apart in the spiral

**How it works:**
```javascript
// Check for overlapping markers
const overlappingMarkers = existingMarkers.filter(m => {
    const pos = m.getPosition();
    return Math.abs(pos.lat() - lat) < 0.0001 && Math.abs(pos.lng() - lng) < 0.0001;
});

// Apply spiral offset
if (overlappingMarkers.length > 0) {
    const offsetCount = overlappingMarkers.length;
    const offsetDistance = 0.00045; // ~50 meters
    const angle = (offsetCount * 60) * (Math.PI / 180);
    const offsetLat = offsetDistance * Math.cos(angle);
    const offsetLng = offsetDistance * Math.sin(angle) / Math.cos(lat * Math.PI / 180);
    
    lat = lat + offsetLat;
    lng = lng + offsetLng;
}
```

### Fix #2: Store Original Coordinates ✅
**File:** `src/frontend/app.js`

**What it does:**
- Stores original coordinates in marker data (`marker.originalLat`, `marker.originalLng`)
- Tracks if marker was offset (`marker.isOffset`)
- Uses marker's actual position for isochrone generation (so isochrone is centered on visible marker)

### Fix #3: User Feedback ✅
**File:** `src/frontend/app.js` - `loadSAMProjects()` function

**What it does:**
- Detects when multiple projects share identical coordinates
- Shows warning toast when 3+ projects share the same location
- Explains that projects may have been geocoded to a general location (e.g., state center)
- Shows note in info window when marker was offset

**Warning Message:**
```
"Warning: 11 projects share the same coordinates. They may have been geocoded to a general location (e.g., state center). Markers have been offset for visibility."
```

## Testing the Fix

### Expected Behavior After Fix:
1. **All 11 markers should be visible** (not stacked)
2. **Markers should be slightly offset** in a circular pattern around the original location
3. **Warning toast should appear** explaining why markers are offset
4. **Info windows should show** a note if marker was offset
5. **Isochrones should be centered** on the visible marker position

### How to Verify:
1. Search for NAICS code "238"
2. Count visible markers on the map (should see 11, not 1)
3. Zoom in on the marker cluster - should see markers spread in a circle
4. Click on markers - info window should show offset warning if applicable
5. Generate isochrone - should be centered on the visible marker

## Long-Term Solution

### Improve Geocoding (Future Enhancement)
The root cause is that many SAM.gov projects only have state-level addresses. To improve this:

1. **Extract more address fields** from SAM.gov data
2. **Try multiple address formats** before falling back to state-only
3. **Use project title + location** for better geocoding (e.g., "Project Name, Richmond, VA")
4. **Consider using project-specific location data** if available in SAM.gov response

### Alternative: Marker Clustering
For production, consider using Google Maps **Marker Clustering** library:
- Groups nearby markers into clusters
- Shows cluster count (e.g., "11")
- Expands to show individual markers when zoomed in
- Better UX for large numbers of overlapping markers

## Files Modified

1. `src/frontend/app.js`
   - `addSAMMarker()` - Added offset detection and spiral pattern
   - `addPlaceMarker()` - Added offset detection and spiral pattern
   - `createSAMInfoContent()` - Uses marker position, shows offset warning
   - `createPlaceInfoContent()` - Uses marker position, shows offset warning
   - `loadSAMProjects()` - Detects duplicate coordinates, shows warning

## Status

✅ **Fix implemented and ready for testing**

The fix will:
- Make all 11 markers visible (not stacked)
- Center isochrones on visible markers
- Provide user feedback about why markers are offset

**Note:** The frontend changes require a page refresh to take effect. Backend changes are already live.

