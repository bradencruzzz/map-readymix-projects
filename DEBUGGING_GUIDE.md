# SiteScoutLite Debugging Guide

## Issues Identified

### 1. Only 2 out of 13 SAM.gov locations appearing on map
### 2. Isochrone appearing as tiny blue shape in bottom corner

---

## Fixes Applied

### Geocoding Improvements

**File: `src/backend/sam_client.py`**

1. **Enhanced address extraction** (lines 18-83)
   - Now handles `placeOfPerformance` as both object AND string
   - Better fallback chain: placeOfPerformance → officeAddress → pointOfContact
   - Handles multiple field name variations (zip, zipcode, zipCode)

2. **Improved address building** (lines 85-130)
   - Works with partial address data
   - Omits "USA" (Google assumes USA by default)
   - More lenient requirements

3. **Flexible state filtering** (lines 270-277)
   - Accepts: "VA", "Virginia", "va", "virginia" (case-insensitive)

4. **Comprehensive error logging** (lines 148-168)
   - Logs EVERY geocoding attempt with result
   - Shows raw SAM.gov data for failed geocodes
   - Helps identify data structure issues

5. **Summary statistics** (lines 280-290)
   - Shows how many projects geocoded successfully
   - Warns about missing coordinates

### Isochrone Improvements

**File: `src/backend/iso_client.py`**

1. **Fixed coordinate parsing priority** (lines 226-262)
   - Now tries object format `{"lat": ..., "lng": ...}` FIRST
   - TravelTime API returns objects, not arrays
   - This was likely causing coordinate parsing failures

2. **Better credential detection** (lines 42-47)
   - Clearly logs when credentials are missing
   - Shows which specific credential is missing

**File: `src/frontend/app.js`**

1. **Added center point logging** (lines 475-479)
   - Helps verify isochrone is centered correctly
   - Compare expected vs actual center

### Logging Improvements

**File: `src/backend/main.py`**

1. **Debug level logging** (lines 24-27)
   - All API calls and responses are now logged
   - Essential for troubleshooting

**File: `src/backend/geocode_client.py`**

1. **Detailed Google API status logging** (lines 48-61)
   - Shows exact Google Geocoding API error codes
   - Identifies REQUEST_DENIED, ZERO_RESULTS, OVER_QUERY_LIMIT, etc.

---

## How to Debug

### Step 1: Restart Your Backend Server

```bash
cd "c:\Users\bzcru\OneDrive\Projects\SiteScoutLite"
python src/backend/main.py
```

Watch for startup messages showing which API keys are detected.

### Step 2: Open Browser DevTools

1. Open your app in browser
2. Press F12 to open DevTools
3. Go to Console tab
4. Go to Network tab

### Step 3: Load SAM Projects

1. Click "Load SAM Projects" or search for projects
2. Watch BOTH:
   - **Backend console** (Python terminal)
   - **Browser console** (DevTools)

### Step 4: Analyze Backend Logs

Look for these log messages:

#### Successful Geocoding
```
[noticeId] Geocoding: 'Richmond, VA, 23219'
[noticeId] SUCCESS: (37.5410, -77.4386)
```

#### Failed Geocoding
```
[noticeId] GEOCODE FAILED
  Title: Project Title Here
  Address: Richmond, VA
  Location fields: {'city': 'Richmond', 'state': 'VA', ...}
  Raw placeOfPerformance: {...}
  Raw officeAddress: {...}
```

**What to check:**
- Is the address valid? (Google should be able to find it)
- Are the location fields correct?
- Is placeOfPerformance a string or object?
- Is there an officeAddress we can use instead?

#### No Address Built
```
[noticeId] NO ADDRESS - Cannot geocode
  Title: Project Title Here
  Location fields: {'city': None, 'state': None, ...}
  Raw placeOfPerformance: ...
  Raw officeAddress: ...
```

**What to check:**
- Are placeOfPerformance and officeAddress both empty?
- Is the data structure different than expected?
- Look at the "Raw" fields to see actual SAM.gov data structure

#### Summary Statistics
```
SAM.gov filtering results: 50 total → 13 accepted
  Filtered out: 20 inactive, 15 non-USA, 2 wrong state
  Geocoding results: 2 with coordinates, 11 without coordinates
  ⚠ 11 projects will NOT appear on map (missing coordinates)
```

This tells you exactly how many projects will appear on the map.

### Step 5: Analyze Isochrone Generation

1. Click on a marker
2. Click "Generate Isochrone"
3. Watch browser console for:

```
[Isochrone] Button clicked for (lat, lng)
[Isochrone] Starting generation for 30 minutes at (lat, lng)
[Isochrone] Center from API: [lng, lat]
[Isochrone] Expected center: [lng, lat]
[Isochrone] Converted N valid coordinates
[Isochrone] Coordinate bounds: {latMin, latMax, lngMin, lngMax}
```

**What to check:**
- Do the center coordinates match?
- Are the bounds in Virginia? (lat: 36.5-39.5, lng: -83.5 to -75.0)
- If bounds are WAY off, coordinates might be swapped

### Step 6: Check Google API Errors

If geocoding fails, look for:

```
Google Geocoding returned status: REQUEST_DENIED
  → API request denied! Check your GOOGLE_MAPS_API_KEY
  → Error message: ...
```

**Common statuses:**
- `ZERO_RESULTS`: Google couldn't find the address (address is invalid/incomplete)
- `REQUEST_DENIED`: API key is invalid or disabled
- `OVER_QUERY_LIMIT`: You've exceeded your Google API quota
- `INVALID_REQUEST`: Request format is wrong

---

## Common Issues & Solutions

### Issue: "REQUEST_DENIED" from Google Geocoding

**Solution:**
1. Check your Google Maps API key is valid
2. Verify Geocoding API is enabled in Google Cloud Console
3. Check API key restrictions (HTTP referrers, IP addresses)

### Issue: "ZERO_RESULTS" for valid-looking addresses

**Solution:**
1. Check if address is too vague (e.g., just "VA")
2. Try with more specific address (city + state + zip)
3. Some SAM.gov addresses might be invalid/incomplete

### Issue: Most addresses show "NO ADDRESS - Cannot geocode"

**Solution:**
1. Check the SAM.gov data structure in logs
2. Look at "Raw placeOfPerformance" field
3. It might be a STRING instead of an object
4. The code now handles this, but check logs to confirm

### Issue: Isochrone appears in wrong location

**Solution:**
1. Check browser console for "Center from API" vs "Expected center"
2. Look at "Coordinate bounds" - should be in Virginia
3. If lat/lng are swapped, file a bug report with exact coordinates

---

## Testing Tools

### Test Geocoding Only
```bash
python test_fixes.py
```

This tests:
- API keys are set
- Google Geocoding works
- TravelTime Isochrones work

### Test Isochrone Coordinates
```bash
python debug_isochrone.py
```

This shows:
- Full isochrone response structure
- Coordinate format (array vs object)
- Whether coordinates are in Virginia

---

## Next Steps

1. **Restart backend** with fixes
2. **Load SAM projects** and watch logs
3. **Copy failing geocode logs** and share them
4. **Test isochrone** and check browser console
5. **Share logs** showing the exact failures

The enhanced logging will show us EXACTLY what's wrong with each project that fails to appear on the map.
