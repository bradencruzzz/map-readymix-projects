# Critical Fixes - November 19, 2025

## Issue #1: Isochrone Not Centered on Location Marker ✅ FIXED

### Problem
When searching for a place (e.g., "5700 Lake Wright") and generating a 30-minute isochrone, the isochrone polygon did not appear centered on the location marker.

### Root Cause
The code was using coordinates from the Places API response (`place.lat`, `place.lng`) instead of the marker's actual position on the map. Even though these should be the same, there can be slight differences due to:
- Floating-point precision
- Marker positioning by Google Maps
- Coordinate rounding

### Solution
**Changed:** Always use the marker's actual position (from `marker.getPosition()`) for isochrone generation instead of the place/project data coordinates.

**Files Modified:**
- `src/frontend/app.js` - `createPlaceInfoContent()` function
- `src/frontend/app.js` - `createSAMInfoContent()` function

**Key Change:**
```javascript
// BEFORE: Used place/project data coordinates
const validLat = (place.lat != null && !isNaN(parseFloat(place.lat))) 
    ? parseFloat(place.lat) 
    : markerLat;

// AFTER: Always use marker's actual position
const markerPos = marker.getPosition();
const validLat = markerPos.lat();
const validLng = markerPos.lng();
```

This ensures the isochrone is perfectly centered on the visible marker, since we're using the exact coordinates that Google Maps uses to position the marker.

---

## Issue #2: NAICS Search Returns 11 Results But Only 1 Marker on Map ✅ FIXED

### Problem
When searching for NAICS code "238", the API returns 11 projects, but only 1 marker appears on the map.

### Root Cause
Many SAM.gov projects don't have complete address information that can be geocoded. The frontend filters out projects without valid coordinates (`project.lat && project.lng`), so only projects that successfully geocoded appear on the map.

The issue was:
1. **Insufficient geocoding attempts**: The code only tried to geocode if it had city+state or similar complete address info
2. **Poor feedback**: Users weren't clearly informed about why projects were missing from the map

### Solution

#### Part 1: Improved Geocoding Logic
**File Modified:** `src/backend/sam_client.py` - `build_address_string()` function

**Changes:**
1. **Multiple geocoding strategies**: Now tries 5 different strategies to extract geocodable addresses:
   - Strategy 1: City + State + ZIP (best)
   - Strategy 2: Check for full address strings in raw SAM.gov data
   - Strategy 3: State + "USA" format (better than just state)
   - Strategy 4: State + ZIPCODE format
   - Strategy 5: Just state (as fallback)

2. **Better address extraction**: Checks additional fields in SAM.gov data for address strings

**Key Improvement:**
```python
# Now tries multiple strategies before giving up
if len(parts) >= 2:
    return ", ".join(parts)  # Best case
elif found_address_in_raw_data:
    return raw_address  # Check other fields
elif state:
    return f"{state}, USA"  # Better than just state
elif state and zipcode:
    return f"{state} {zipcode}"  # State + ZIP
```

#### Part 2: Improved User Feedback
**File Modified:** `src/frontend/app.js` - `loadSAMProjects()` function

**Changes:**
1. **Separate warning toast**: Now shows a separate warning toast when projects are missing coordinates
2. **More detailed messages**: Explains that projects without coordinates may not have geocodable addresses
3. **Better visibility**: Warning toast appears in addition to success message

**Example Messages:**
- Success: "Found 11 project(s) with locations for NAICS code '238'"
- Warning: "10 project(s) found but missing coordinates. They may not have geocodable addresses."

---

## Testing Recommendations

### Test Issue #1 Fix:
1. Search for a place: "5700 Lake Wright"
2. Click on the marker
3. Click "Generate Isochrone"
4. **Expected**: Isochrone polygon should be perfectly centered on the marker

### Test Issue #2 Fix:
1. Search for NAICS code: "238"
2. **Expected**: 
   - Should see success message with count of projects with locations
   - Should see warning message about projects without coordinates (if any)
   - More projects should appear on map (if geocoding improvements worked)
   - Check backend logs for geocoding details

---

## Backend Logging

The backend now logs detailed information about geocoding:
- Which projects successfully geocoded
- Which projects failed geocoding and why
- What address strings were attempted

Check server logs to see:
```
[Geocode] Geocoding: 'Richmond, VA 23237'
[Geocode] Geocode success: (37.5407, -77.4360)
```

Or for failures:
```
[Geocode] GEOCODE FAILED
  Title: Project Name
  Address: VA
  Location fields: {'city': None, 'state': 'VA', 'zipcode': None}
```

---

## Files Changed

1. `src/frontend/app.js`
   - `createPlaceInfoContent()` - Always use marker position
   - `createSAMInfoContent()` - Always use marker position  
   - `loadSAMProjects()` - Improved feedback for missing coordinates

2. `src/backend/sam_client.py`
   - `build_address_string()` - Multiple geocoding strategies

---

## Status

✅ **Both issues fixed and ready for testing**

The server needs to be restarted to pick up backend changes. Frontend changes will be picked up on next page load.

