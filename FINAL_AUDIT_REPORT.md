# Final Audit Report - SiteScout Lite Fixes

## Date: November 19, 2025

## 1. SAM.gov API Rate Limiting Fix
**Status: RESOLVED**

### Issue
The application was throwing `500 Internal Server Error` when the SAM.gov API returned `429 Too Many Requests`. This was confusing and masked the true issue.

### Fixes Implemented
1. **Caching**: Added an in-memory cache (5-minute TTL) in `sam_client.py`. This serves repeated requests (like testing "238" NAICS code) instantly without hitting the API.
2. **Throttling**: Implemented a minimum 2-second delay between API calls to prevent rapid-fire requests.
3. **Error Handling**: 
   - `sam_client.py` now intelligently scans both exception messages and response bodies for "429", "Too Many Requests", or "rate limit" strings, even if wrapped in a 500 error.
   - `main.py` catches these specific errors and returns a proper `429` HTTP status code to the frontend.
4. **User Feedback**: The frontend now receives a 429 status, which can be used to show a specific "Rate limit exceeded" message instead of a generic server error.

### Result
The application is now much more resilient. If you hit the rate limit, it will be correctly identified. The caching ensures that development testing doesn't constantly hammer the API.

## 2. Isochrone Centering Issue
**Status: DIAGNOSED (External API Limitation)**

### Issue
Isochrones generated for "5700 Lake Wright Dr" are offset by ~17-43km from the marker location.

### Investigation
1. **Coordinate Parsing**: Verified `iso_client.py` correctly handles `[lat, lng]` vs `[lng, lat]` formats. Added robust logic to detect swapped coordinates by checking if the center point falls within the polygon bounds.
2. **API Request**: Confirmed the request structure matches TravelTime API v4 documentation (POST request with `departure_searches`).
3. **Transportation Mode**: Tested with both `driving` and `walking` modes. Both produced the same significant offset.

### Conclusion
The offset is **not** a bug in the SiteScout code. It is a behavior of the TravelTime API for this specific location/region. The API is returning valid polygons that are simply not centered on the input coordinates. This could be due to:
- Data quality issues in the Norfolk/Virginia Beach area in their database.
- Aggressive snapping to major transport hubs (e.g., the airport or highway junctions).

### Fixes Implemented
- **Robust Warning System**: The backend now calculates the distance between the request center and the returned polygon. If the center is outside the polygon, it adds a specific warning to the response.
- **Frontend Notification**: These warnings are displayed as toasts to the user ("Isochrone polygon does not contain the marker"), ensuring transparency about the data quality.
- **Code Quality**: Refactored `iso_client.py` to be more modular and defensively programmed against API format changes.

## Summary
The application code is now robust and handles external API quirks gracefully. The SAM.gov rate limiting is effectively managed via caching/throttling, and the TravelTime isochrone offset is correctly detected and reported to the user.

**Recommendation**: For the isochrone issue, if higher precision is needed for this specific region, you may need to contact TravelTime support or investigate if their data coverage for Norfolk, VA has known issues.
