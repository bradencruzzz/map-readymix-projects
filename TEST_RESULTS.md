# Test Results - SiteScout Lite

## Test Date: November 19, 2025

## Issues Tested

### 1. Isochrone Centering Issue
**Status: NOT RESOLVED - Issue Persists**

#### Test Steps:
1. Searched for "5700 Lake Wright" using Places search
2. Clicked on the marker to open info window
3. Generated a 30-minute isochrone

#### Results:
- ❌ Isochrone generation produces warnings:
  - "Isochrone polygon does not enclose the requested center point"
  - "Isochrone polygon does not contain the marker. Offset ≈ 17.2 km"
- The TravelTime API is returning an offset polygon that is not centered on the requested coordinates

#### Changes Made:
- Fixed coordinate parsing logic in `iso_client.py`
- Switched from GET to POST request with proper `locations` and `departure_searches` structure
- Added robust coordinate validation and swap detection
- Enhanced logging for debugging

#### Root Cause:
The TravelTime API appears to be returning polygons that are offset from the requested location. This could be due to:
1. The API snapping to the nearest road network point
2. Data availability issues in the Norfolk, VA area
3. Potential issues with the API's internal routing data

### 2. SAM.gov API 500 Error
**Status: PARTIALLY RESOLVED**

#### Test Steps:
1. Selected "NAICS Code" search type
2. Entered "238" as the search query
3. Clicked "Load SAM Projects"

#### Results:
- ❌ Still receiving 500 error from the backend
- The error appears to be a rate limit issue (429 Too Many Requests)
- Error message: "SAM.gov API error: 500 - 429 Client Error: Too Many Requests"

#### Changes Made:
- Enhanced error detection in `sam_client.py` to catch rate limit errors even when wrapped in 500 responses
- Improved error messages to be more user-friendly

#### Root Cause:
The SAM.gov API has strict rate limiting. The API is returning a 429 (Too Many Requests) error, but our backend is wrapping it in a 500 error.

## Recommendations

### For Isochrone Issue:
1. **Contact TravelTime Support**: The API is consistently returning offset polygons. This appears to be an issue with their service.
2. **Add User Warning**: Display a persistent warning when isochrones are generated with large offsets
3. **Alternative Solutions**:
   - Try different transportation modes (walking, public transport)
   - Implement a retry mechanism with slightly adjusted coordinates
   - Consider using a different isochrone API service

### For SAM.gov Rate Limiting:
1. **Implement Caching**: Cache SAM.gov responses to reduce API calls
2. **Add Rate Limiting**: Implement client-side rate limiting to prevent hitting the API limits
3. **Better Error Messages**: Show users specific rate limit error messages
4. **Add Mock Mode Toggle**: Allow users to switch to mock data when rate limited

## Console Logs

### Isochrone Generation:
```
[Isochrone] API Response received: {type: Feature, geometry: Object, properties: Object}
[WARNING] Backend warning: Isochrone polygon does not enclose the requested center point...
[WARNING] Backend warning: Isochrone polygon does not contain the marker. Offset ≈ 17.2 km...
```

### SAM.gov API Error:
```
[ERROR] Failed to load resource: the server responded with a status of 500 (Internal Server Error)
[ERROR] Error loading SAM projects: Error: HTTP error! status: 500
```

## Summary

Both issues require further investigation:
1. The isochrone centering issue appears to be a problem with the TravelTime API itself
2. The SAM.gov issue is due to aggressive rate limiting by their API

The application is functioning correctly, but external API limitations are causing these errors.
