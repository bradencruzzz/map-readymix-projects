# TravelTime API Request Comparison

## Working Cloudflare Worker Example

```javascript
const arrival_searches = [];
for (const pt of arrivals) {
  if (typeof pt.lat !== "number" || typeof pt.lng !== "number") continue;
  for (const m of minutes) {
    arrival_searches.push({
      id: `pt_${m}min_${pt.lat.toFixed(5)}_${pt.lng.toFixed(5)}`,
      coords: { lat: pt.lat, lng: pt.lng },
      transportation: { type: "driving" },
      travel_time: m * 60,
      arrival_time: iso
    });
  }
}

const ttResp = await fetch("https://api.traveltimeapp.com/v4/time-map", {
  method: "POST",
  headers: {
    "X-Application-Id": env.TRAVELTIME_APP_ID,
    "X-Api-Key": env.TRAVELTIME_API_KEY,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ arrival_searches })
});
```

## Current Site Scout Lite Implementation

### Request Structure (from iso_client.py lines 243-271)

```python
url = "https://api.traveltimeapp.com/v4/time-map"

headers = {
    "Content-Type": "application/json",
    "X-Application-Id": TRAVELTIME_APP_ID,
    "X-Api-Key": TRAVELTIME_API_KEY
}

arrival_time_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
body = {
    "arrival_searches": [
        {
            "id": f"isochrone_{minutes}min_{lat:.5f}_{lng:.5f}",
            "coords": {
                "lat": float(lat),
                "lng": float(lng)
            },
            "arrival_time": arrival_time_iso,
            "travel_time": int(minutes * 60),
            "transportation": {
                "type": "driving"
            }
        }
    ]
}

response = requests.post(url, json=body, headers=headers, timeout=30)
```

### Actual Request (from test output)

```json
{
  "arrival_searches": [
    {
      "id": "test_30min_37.54072_-77.43605",
      "coords": {
        "lat": 37.5407246,
        "lng": -77.4360481
      },
      "arrival_time": "2025-11-24T06:27:32Z",
      "travel_time": 1800,
      "transportation": {
        "type": "driving"
      }
    }
  ]
}
```

## Comparison Result

| Component | Cloudflare Worker | Site Scout Lite | Match |
|-----------|-------------------|-----------------|-------|
| Endpoint | `/v4/time-map` | `/v4/time-map` | ✅ |
| Method | POST | POST | ✅ |
| Header: X-Application-Id | ✅ | ✅ | ✅ |
| Header: X-Api-Key | ✅ | ✅ | ✅ |
| Header: Content-Type | `application/json` | `application/json` | ✅ |
| Body: `arrival_searches` array | ✅ | ✅ | ✅ |
| Coords format | `{lat, lng}` | `{lat, lng}` | ✅ |
| Coords order | `{lat: number, lng: number}` | `{lat: float, lng: float}` | ✅ |
| transportation.type | `"driving"` | `"driving"` | ✅ |
| travel_time (seconds) | `m * 60` | `minutes * 60` | ✅ |
| arrival_time format | ISO string with `Z` | ISO string with `Z` | ✅ |

## Verdict: ✅ REQUEST STRUCTURE IS CORRECT

The Site Scout Lite implementation **EXACTLY matches** the working Cloudflare Worker example in all critical aspects:

1. **Coordinates are sent in correct order**: `{lat, lng}`
2. **Headers are correct**: `X-Application-Id` and `X-Api-Key`
3. **Time conversion is correct**: minutes × 60 = seconds
4. **Transportation type is correct**: `"driving"`
5. **Endpoint is correct**: `/v4/time-map` with POST method

## Response Format (from actual API call)

TravelTime returns coordinates as **OBJECTS**:

```json
{
  "results": [{
    "shapes": [{
      "shell": [
        {"lat": 37.495472, "lng": -77.73261},
        {"lat": 37.496174, "lng": -77.731384},
        ...
      ],
      "holes": []
    }]
  }]
}
```

**NOT** as arrays like `[lng, lat]` or `[lat, lng]`.

## Current Code Handling (iso_client.py lines 140-146)

```python
if isinstance(coord, dict):
    lat_candidate, lng_candidate = _extract_lat_lng_from_object(coord)
    if lat_candidate is not None and lng_candidate is not None:
        lat_val = lat_candidate
        lng_val = lng_candidate
        if coord_format is None:
            coord_format = "object"
```

**This is CORRECT** - it extracts `lat` and `lng` from the dictionary objects.

## Coordinate Conversion Flow

1. **TravelTime returns**: `{lat: 37.495472, lng: -77.73261}`
2. **Extract as tuple**: `(37.495472, -77.73261)` ← (lat, lng)
3. **Store as GeoJSON array**: `[-77.73261, 37.495472]` ← [lng, lat]
4. **Frontend receives**: `[[-77.73261, 37.495472], ...]` (GeoJSON format)
5. **Frontend converts**: `{lat: 37.495472, lng: -77.73261}` for Google Maps

**✅ ALL CONVERSIONS ARE CORRECT**

