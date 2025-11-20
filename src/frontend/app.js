/**
 * Site Scout Lite - Frontend Application
 * Google Maps integration for geospatial analytics
 */

// Map instance and state management
let map;
let samMarkers = [];
let placesMarkers = [];
let activeIsochronePolygon = null;
let activeInfoWindow = null;
let isGeneratingIsochrone = false; // Prevent concurrent isochrone generation

/**
 * Global function to be called from InfoWindow buttons
 * InfoWindows render in a separate context, so we need a global function
 * Define this early to ensure it's available when InfoWindows are created
 */
window.generateIsochroneFromInfo = function(lat, lng) {
    console.log(`[Isochrone] Button clicked for (${lat}, ${lng})`);
    if (typeof generateIsochrone === 'function') {
        generateIsochrone(lat, lng);
    } else {
        console.error("[Isochrone] generateIsochrone function not available yet");
        alert("Map is still loading. Please wait a moment and try again.");
    }
};

/**
 * Initialize Google Map centered on Richmond, VA
 * No auto-zoom on searches (map view remains unchanged)
 */
function initializeMap() {
    // Center on Richmond, VA (37.5407, -77.4360)
    const richmond = { lat: 37.5407, lng: -77.4360 };
    
    map = new google.maps.Map(document.getElementById("map"), {
        center: richmond,
        zoom: 8,
        mapTypeId: "roadmap",
        disableDefaultUI: false,
        zoomControl: true,
        mapTypeControl: true,
        scaleControl: true,
        streetViewControl: false,
        rotateControl: false,
        fullscreenControl: true
    });
    
    // Set up event listeners
    setupEventListeners();
    
    console.log("Map initialized - centered on Richmond, VA");
}

/**
 * Set up all event listeners for UI controls
 */
function setupEventListeners() {
    // Load SAM Projects button
    document.getElementById("loadSAMBtn").addEventListener("click", loadSAMProjects);
    
    // SAM search on Enter key
    document.getElementById("samSearchInput").addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            loadSAMProjects();
        }
    });
    
    // Update placeholder based on search type
    document.getElementById("samSearchType").addEventListener("change", (e) => {
        const searchInput = document.getElementById("samSearchInput");
        if (e.target.value === "naics") {
            searchInput.placeholder = "e.g., 327300, 238110...";
        } else {
            searchInput.placeholder = "e.g., concrete, cement...";
        }
    });
    
    // Search Places button
    document.getElementById("searchPlacesBtn").addEventListener("click", searchPlaces);
    
    // Search Places on Enter key
    document.getElementById("placesSearch").addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            searchPlaces();
        }
    });
}

/**
 * Load SAM.gov projects from /api/projects endpoint
 * Uses keyword search or NAICS code search based on user selection
 */
async function loadSAMProjects() {
    try {
        const searchQuery = document.getElementById("samSearchInput").value.trim();
        const searchType = document.getElementById("samSearchType").value;
        
        // Build API URL with optional search query and type
        // Support mock mode via URL parameter (for testing: add &mock=true to URL)
        const urlParams = new URLSearchParams(window.location.search);
        const useMock = urlParams.get('mock') === 'true';
        
        let apiUrl = "/api/projects";
        const params = new URLSearchParams();
        
        if (searchQuery) {
            params.append("q", searchQuery);
            params.append("search_type", searchType);
        }
        
        if (useMock) {
            params.append("mock", "true");
        }
        
        if (params.toString()) {
            apiUrl += "?" + params.toString();
        }
        
        const searchTypeLabel = searchType === "naics" ? "NAICS code" : "keyword";
        const searchMsg = searchQuery 
            ? `Searching SAM projects by ${searchTypeLabel}: "${searchQuery}"...` 
            : "Loading SAM projects...";
        showToast(searchMsg, "info");
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const projects = await response.json();
        
        if (!Array.isArray(projects) || projects.length === 0) {
            const noResultsMsg = searchQuery 
                ? `No projects found for ${searchTypeLabel} "${searchQuery}"` 
                : "No projects found";
            showToast(noResultsMsg, "warning");
            return;
        }
        
        // Clear existing SAM markers
        clearSAMMarkers();
        
        // Add markers for each project and count how many have valid coordinates
        let validProjectCount = 0;
        let withoutCoordsCount = 0;
        const coordinateMap = new Map(); // Track coordinates to detect duplicates
        
        projects.forEach(project => {
            if (project.lat && project.lng) {
                // Track coordinate usage to detect when multiple projects share same location
                const coordKey = `${project.lat.toFixed(6)},${project.lng.toFixed(6)}`;
                if (!coordinateMap.has(coordKey)) {
                    coordinateMap.set(coordKey, []);
                }
                coordinateMap.get(coordKey).push(project);
                
                addSAMMarker(project);
                validProjectCount++;
            } else {
                withoutCoordsCount++;
            }
        });
        
        // Check for duplicate coordinates (likely all geocoded to same location like state center)
        const duplicateCoords = Array.from(coordinateMap.entries()).filter(([coord, projs]) => projs.length > 1);
        if (duplicateCoords.length > 0) {
            const totalDuplicates = duplicateCoords.reduce((sum, [coord, projs]) => sum + projs.length, 0);
            if (totalDuplicates > 3) {
                showToast(
                    `Warning: ${totalDuplicates} projects share the same coordinates. They may have been geocoded to a general location (e.g., state center). Markers have been offset for visibility.`,
                    "warning"
                );
            }
        }
        
        // Show message with actual count of displayed markers
        // Make it more prominent if many projects are missing coordinates
        let successMsg;
        if (searchQuery) {
            successMsg = `Found ${validProjectCount} project(s) with locations for ${searchTypeLabel} "${searchQuery}"`;
            if (withoutCoordsCount > 0) {
                successMsg += ` (${withoutCoordsCount} without coordinates - check backend logs for geocoding details)`;
                // Show warning toast for projects without coordinates
                showToast(`${withoutCoordsCount} project(s) found but missing coordinates. They may not have geocodable addresses.`, "warning");
            }
        } else {
            successMsg = `Loaded ${validProjectCount} projects`;
            if (withoutCoordsCount > 0) {
                successMsg += ` (${withoutCoordsCount} without coordinates)`;
                showToast(`${withoutCoordsCount} project(s) missing coordinates. Check backend logs for geocoding details.`, "warning");
            }
        }
        showToast(successMsg, "success");
        
    } catch (error) {
        console.error("Error loading SAM projects:", error);
        showToast("Error loading projects: " + error.message, "error");
    }
}

/**
 * Add a SAM project marker to the map
 * If multiple markers have identical coordinates, adds a small offset to prevent stacking
 */
function addSAMMarker(project) {
    // Check if we already have a marker at this exact location
    // If so, add a small random offset (spiral pattern) to make it visible
    let lat = project.lat;
    let lng = project.lng;
    
    // Check for overlapping markers
    const existingMarkers = samMarkers.map(m => m.marker);
    const overlappingMarkers = existingMarkers.filter(m => {
        const pos = m.getPosition();
        return pos && Math.abs(pos.lat() - lat) < 0.0001 && Math.abs(pos.lng() - lng) < 0.0001;
    });
    
    // If there are overlapping markers, add a small offset using a spiral pattern
    if (overlappingMarkers.length > 0) {
        const offsetCount = overlappingMarkers.length;
        // Spiral offset: each overlapping marker gets offset in a circle
        // ~50 meters per offset (0.00045 degrees ≈ 50m)
        const offsetDistance = 0.00045; // degrees
        const angle = (offsetCount * 60) * (Math.PI / 180); // 60 degrees between markers
        const offsetLat = offsetDistance * Math.cos(angle);
        const offsetLng = offsetDistance * Math.sin(angle) / Math.cos(lat * Math.PI / 180);
        
        lat = lat + offsetLat;
        lng = lng + offsetLng;
        
        console.log(`[SAM Marker] Offset marker ${offsetCount} at (${project.lat}, ${project.lng}) to (${lat.toFixed(6)}, ${lng.toFixed(6)}) to prevent stacking`);
    }
    
    const marker = new google.maps.Marker({
        position: { lat: lat, lng: lng },
        map: map,
        title: project.title || "SAM Project",
        icon: {
            url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png",
            scaledSize: new google.maps.Size(32, 32)
        }
    });
    
    // Store original coordinates in marker data for isochrone generation
    // This ensures isochrones use the actual project location, not the offset marker position
    marker.originalLat = project.lat;
    marker.originalLng = project.lng;
    marker.isOffset = (Math.abs(lat - project.lat) > 0.0001 || Math.abs(lng - project.lng) > 0.0001);
    
    // Create info window content
    const infoContent = createSAMInfoContent(project, marker);
    const infoWindow = new google.maps.InfoWindow({
        content: infoContent
    });
    
    // Click handler: open info window
    marker.addListener("click", () => {
        // Close any previously open info window
        if (activeInfoWindow) {
            activeInfoWindow.close();
        }
        
        infoWindow.open(map, marker);
        activeInfoWindow = infoWindow;
    });
    
    samMarkers.push({ marker, infoWindow });
}

/**
 * Create HTML content for SAM project info card
 */
function createSAMInfoContent(project, marker) {
    const formatCurrency = (amount) => {
        if (!amount) return "N/A";
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    };
    
    const address = project.city && project.state && project.zipcode
        ? `${escapeHtml(project.city)}, ${escapeHtml(project.state)} ${escapeHtml(project.zipcode)}`
        : (project.address || "N/A");
    
    // Use marker's actual position for isochrone generation
    // This ensures isochrones are centered on the visible marker (even if offset to prevent stacking)
    const markerPos = marker.getPosition();
    const markerLat = markerPos.lat();
    const markerLng = markerPos.lng();
    
    const validLat = markerLat;
    const validLng = markerLng;
    
    // Show warning if marker was offset
    const offsetWarning = marker.isOffset 
        ? '<div class="info-field" style="color: #ff9800; font-size: 12px; margin-top: 8px;"><em>Note: Marker offset to prevent stacking with other locations</em></div>'
        : '';
    
    return `
        <div class="info-card">
            <h3 class="info-title">${escapeHtml(project.title || "Untitled Project")}</h3>
            <div class="info-field">
                <span class="info-label">Project type:</span>
                <span class="info-value">${escapeHtml(project.project_type || "N/A")}</span>
            </div>
            <div class="info-field">
                <span class="info-label">NAICS:</span>
                <span class="info-value">${escapeHtml(project.naics || "N/A")}</span>
            </div>
            <div class="info-field">
                <span class="info-label">Department:</span>
                <span class="info-value">${escapeHtml(project.department || "N/A")}</span>
            </div>
            <div class="info-field">
                <span class="info-label">Location:</span>
                <span class="info-value">${address}</span>
            </div>
            ${project.coordinates_source ? `
            <div class="info-field">
                <span class="info-label">Coord source:</span>
                <span class="info-value">${escapeHtml(project.coordinates_source)}</span>
            </div>` : ''}
            <div class="info-field">
                <span class="info-label">Est. award:</span>
                <span class="info-value">${formatCurrency(project.estimated_award_amount)}</span>
            </div>
            ${project.ui_link ? `
                <div class="info-link">
                    <a href="${escapeHtml(project.ui_link)}" target="_blank">View on SAM.gov</a>
                </div>
            ` : ''}
            ${offsetWarning}
            <button class="btn-isochrone" onclick="window.generateIsochroneFromInfo(${validLat}, ${validLng})">
                Generate Isochrone
            </button>
        </div>
    `;
}

/**
 * Search for places using /api/places endpoint
 */
async function searchPlaces() {
    const query = document.getElementById("placesSearch").value.trim();
    
    if (!query) {
        showToast("Please enter a search query", "warning");
        return;
    }
    
    try {
        showToast(`Searching for "${query}"...`, "info");
        
        const response = await fetch(`/api/places?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const places = await response.json();
        
        if (!Array.isArray(places) || places.length === 0) {
            showToast("No places found", "warning");
            return;
        }
        
        // Clear existing places markers
        clearPlacesMarkers();
        
        // Add markers for each place and count how many have valid coordinates
        let validPlaceCount = 0;
        places.forEach(place => {
            if (place.lat && place.lng) {
                addPlaceMarker(place);
                validPlaceCount++;
            }
        });
        
        showToast(`Found ${validPlaceCount} places${validPlaceCount < places.length ? ` (${places.length - validPlaceCount} without coordinates)` : ''}`, "success");
        
        // No auto-zoom - map view remains unchanged per requirements
        
    } catch (error) {
        console.error("Error searching places:", error);
        showToast("Error searching places: " + error.message, "error");
    }
}

/**
 * Add a place marker to the map
 * If multiple markers have identical coordinates, adds a small offset to prevent stacking
 */
function addPlaceMarker(place) {
    // Check if we already have a marker at this exact location
    // If so, add a small random offset (spiral pattern) to make it visible
    let lat = place.lat;
    let lng = place.lng;
    
    // Check for overlapping markers
    const existingMarkers = placesMarkers.map(m => m.marker);
    const overlappingMarkers = existingMarkers.filter(m => {
        const pos = m.getPosition();
        return pos && Math.abs(pos.lat() - lat) < 0.0001 && Math.abs(pos.lng() - lng) < 0.0001;
    });
    
    // If there are overlapping markers, add a small offset using a spiral pattern
    if (overlappingMarkers.length > 0) {
        const offsetCount = overlappingMarkers.length;
        // Spiral offset: each overlapping marker gets offset in a circle
        // ~50 meters per offset (0.00045 degrees ≈ 50m)
        const offsetDistance = 0.00045; // degrees
        const angle = (offsetCount * 60) * (Math.PI / 180); // 60 degrees between markers
        const offsetLat = offsetDistance * Math.cos(angle);
        const offsetLng = offsetDistance * Math.sin(angle) / Math.cos(lat * Math.PI / 180);
        
        lat = lat + offsetLat;
        lng = lng + offsetLng;
        
        console.log(`[Place Marker] Offset marker ${offsetCount} at (${place.lat}, ${place.lng}) to (${lat.toFixed(6)}, ${lng.toFixed(6)}) to prevent stacking`);
    }
    
    const marker = new google.maps.Marker({
        position: { lat: lat, lng: lng },
        map: map,
        title: place.name || "Place",
        icon: {
            url: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
            scaledSize: new google.maps.Size(32, 32)
        }
    });
    
    // Store original coordinates in marker data for isochrone generation
    // This ensures isochrones use the actual place location, not the offset marker position
    marker.originalLat = place.lat;
    marker.originalLng = place.lng;
    marker.isOffset = (Math.abs(lat - place.lat) > 0.0001 || Math.abs(lng - place.lng) > 0.0001);
    
    // Create info window content
    const infoContent = createPlaceInfoContent(place, marker);
    const infoWindow = new google.maps.InfoWindow({
        content: infoContent
    });
    
    // Click handler: open info window
    marker.addListener("click", () => {
        // Close any previously open info window
        if (activeInfoWindow) {
            activeInfoWindow.close();
        }
        
        infoWindow.open(map, marker);
        activeInfoWindow = infoWindow;
    });
    
    placesMarkers.push({ marker, infoWindow });
}

/**
 * Create HTML content for place info card
 */
function createPlaceInfoContent(place, marker) {
    // Use marker's actual position for isochrone generation
    // This ensures isochrones are centered on the visible marker (even if offset to prevent stacking)
    const markerPos = marker.getPosition();
    const markerLat = markerPos.lat();
    const markerLng = markerPos.lng();
    
    const validLat = markerLat;
    const validLng = markerLng;
    
    // Show warning if marker was offset
    const offsetWarning = marker.isOffset 
        ? '<div class="info-field" style="color: #ff9800; font-size: 12px; margin-top: 8px;"><em>Note: Marker offset to prevent stacking with other locations</em></div>'
        : '';
    
    return `
        <div class="info-card">
            <h3 class="info-title">${escapeHtml(place.name || "Place")}</h3>
            <div class="info-field">
                <span class="info-label">Address:</span>
                <span class="info-value">${escapeHtml(place.address || "N/A")}</span>
            </div>
            ${offsetWarning}
            <button class="btn-isochrone" onclick="window.generateIsochroneFromInfo(${validLat}, ${validLng})">
                Generate Isochrone
            </button>
        </div>
    `;
}

/**
 * Generate isochrone polygon from /api/isochrones endpoint
 * Triggered by "Generate Isochrone" button click
 */
async function generateIsochrone(lat, lng) {
    // Prevent concurrent requests
    if (isGeneratingIsochrone) {
        console.log("[Isochrone] Generation already in progress, ignoring duplicate request");
        return;
    }
    
    // Ensure map is initialized
    if (!map) {
        console.error("[Isochrone] Map not initialized yet");
        showToast("Map not ready. Please wait...", "error");
        return;
    }
    
    // Validate and convert coordinates to numbers
    const parsedLat = parseFloat(lat);
    const parsedLng = parseFloat(lng);
    
    // Check if coordinates are valid numbers
    if (isNaN(parsedLat) || isNaN(parsedLng)) {
        console.error(`[Isochrone] Invalid coordinates: lat=${lat} (${typeof lat}), lng=${lng} (${typeof lng})`);
        showToast("Invalid coordinates. Cannot generate isochrone.", "error");
        return;
    }
    
    // Validate coordinate ranges
    if (!(-90 <= parsedLat && parsedLat <= 90) || !(-180 <= parsedLng && parsedLng <= 180)) {
        console.error(`[Isochrone] Coordinates out of range: lat=${parsedLat}, lng=${parsedLng}`);
        showToast("Coordinates out of valid range. Cannot generate isochrone.", "error");
        return;
    }
    
    // Detect potential coordinate swap (if lat looks like lng and vice versa)
    // US coordinates: lat is typically 25-50, lng is typically -125 to -65
    // If lat is outside typical US range but lng is in typical lat range, they might be swapped
    const typicalUSLatRange = [25, 50];
    const typicalUSLngRange = [-125, -65];
    const latInLngRange = typicalUSLngRange[0] <= parsedLat && parsedLat <= typicalUSLngRange[1];
    const lngInLatRange = typicalUSLatRange[0] <= parsedLng && parsedLng <= typicalUSLatRange[1];
    
    if (latInLngRange && lngInLatRange) {
        console.warn(`[Isochrone] WARNING: Coordinates may be swapped! lat=${parsedLat} (looks like lng), lng=${parsedLng} (looks like lat)`);
        console.warn(`[Isochrone] If isochrone appears in wrong location, coordinates may need to be swapped`);
        // Don't auto-swap, just warn - let the user verify
    }
    
    isGeneratingIsochrone = true;
    
    try {
        const minutes = parseInt(document.getElementById("driveTimeSelect").value);
        
        console.log(`[Isochrone] Starting generation for ${minutes} minutes at (${parsedLat}, ${parsedLng})`);
        console.log(`[Isochrone] Original input: lat=${lat} (${typeof lat}), lng=${lng} (${typeof lng})`);
        console.log(`[Isochrone] Parsed values: lat=${parsedLat}, lng=${parsedLng}`);
        showToast(`Generating ${minutes}-minute isochrone...`, "info");
        
        // Support mock mode via URL parameter (for testing: add &mock=true to URL)
        const urlParams = new URLSearchParams(window.location.search);
        const useMock = urlParams.get('mock') === 'true';
        // Use parsed coordinates to ensure they're numbers
        const apiUrl = `/api/isochrones?lat=${parsedLat}&lng=${parsedLng}&minutes=${minutes}${useMock ? '&mock=true' : ''}`;
        console.log(`[Isochrone] Fetching from: ${apiUrl}`);
        if (useMock) {
            console.log(`[Isochrone] Using MOCK mode (add ?mock=true to URL to test mock polygons)`);
        }
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[Isochrone] API Error - Status: ${response.status}`, errorText);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        
        const geojson = await response.json();
        console.log("[Isochrone] API Response received:", geojson);
        console.log("[Isochrone] Response type:", geojson.type);
        console.log("[Isochrone] Geometry type:", geojson.geometry?.type);
        console.log("[Isochrone] Has coordinates:", !!geojson.geometry?.coordinates);

        // DEBUG: Log the center point from the response
        if (geojson.properties?.center) {
            console.log("[Isochrone] Center from API:", geojson.properties.center);
            console.log("[Isochrone] Expected center: [" + parsedLng + ", " + parsedLat + "]");
        }
        
        const backendWarnings = Array.isArray(geojson.properties?.warnings) ? geojson.properties.warnings : [];
        if (backendWarnings.length > 0) {
            backendWarnings.forEach((message) => {
                console.warn("[Isochrone] Backend warning:", message);
                showToast(message, "warning");
            });
        }
        if (geojson.properties?.selection_reason) {
            console.log("[Isochrone] Shell selection reason:", geojson.properties.selection_reason);
        }
        
        // Validate GeoJSON structure
        if (!geojson.geometry) {
            throw new Error("Invalid GeoJSON: missing geometry");
        }
        if (geojson.geometry.type !== "Polygon") {
            throw new Error(`Invalid geometry type: ${geojson.geometry.type}, expected Polygon`);
        }
        if (!geojson.geometry.coordinates || !Array.isArray(geojson.geometry.coordinates)) {
            throw new Error("Invalid GeoJSON: missing or invalid coordinates array");
        }
        if (!geojson.geometry.coordinates[0] || !Array.isArray(geojson.geometry.coordinates[0])) {
            throw new Error("Invalid GeoJSON: missing or invalid coordinate ring");
        }
        
        const coordinateRing = geojson.geometry.coordinates[0];
        console.log(`[Isochrone] Coordinate ring length: ${coordinateRing.length}`);
        console.log(`[Isochrone] First coordinate:`, coordinateRing[0]);
        console.log(`[Isochrone] Last coordinate:`, coordinateRing[coordinateRing.length - 1]);
        
        // Clear previous isochrone (only if it exists and is valid)
        if (activeIsochronePolygon) {
            try {
                console.log("[Isochrone] Clearing previous polygon");
                activeIsochronePolygon.setMap(null);
            } catch (e) {
                console.warn("[Isochrone] Error clearing previous polygon:", e);
            }
            activeIsochronePolygon = null;
        }
        
        // Convert GeoJSON coordinates to Google Maps format
        // GeoJSON uses [lng, lat], Google Maps uses {lat, lng}
        const coordinates = [];
        let invalidCount = 0;
        
        for (let i = 0; i < coordinateRing.length; i++) {
            const coord = coordinateRing[i];
            if (!Array.isArray(coord) || coord.length < 2) {
                console.warn(`[Isochrone] Invalid coordinate at index ${i}:`, coord);
                invalidCount++;
                continue;
            }
            
            const lng = parseFloat(coord[0]);
            const lat = parseFloat(coord[1]);
            
            if (isNaN(lng) || isNaN(lat)) {
                console.warn(`[Isochrone] NaN coordinate at index ${i}:`, coord);
                invalidCount++;
                continue;
            }
            
            if (!(-180 <= lng && lng <= 180) || !(-90 <= lat && lat <= 90)) {
                console.warn(`[Isochrone] Coordinate out of range at index ${i}: [${lng}, ${lat}]`);
                invalidCount++;
                continue;
            }
            
            coordinates.push({ lat, lng });
        }
        
        if (invalidCount > 0) {
            console.warn(`[Isochrone] Found ${invalidCount} invalid coordinates out of ${coordinateRing.length} total`);
        }
        
        if (coordinates.length < 3) {
            throw new Error(`Not enough valid coordinates: ${coordinates.length} (need at least 3)`);
        }
        
        console.log(`[Isochrone] Converted ${coordinates.length} valid coordinates`);
        console.log(`[Isochrone] Coordinate bounds:`, {
            latMin: Math.min(...coordinates.map(c => c.lat)),
            latMax: Math.max(...coordinates.map(c => c.lat)),
            lngMin: Math.min(...coordinates.map(c => c.lng)),
            lngMax: Math.max(...coordinates.map(c => c.lng))
        });
        
        // Create polygon with TravelTime-like styling
        console.log("[Isochrone] Creating Google Maps Polygon...");
        const polygon = new google.maps.Polygon({
            paths: coordinates,
            strokeColor: "#4285F4",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: "#4285F4",
            fillOpacity: 0.2,
            map: map, // Attach to map immediately
            zIndex: 1 // Ensure polygon appears above markers
        });
        
        // Store reference BEFORE logging (in case logging fails)
        activeIsochronePolygon = polygon;
        
        console.log("[Isochrone] Polygon created:", polygon);
        console.log("[Isochrone] Polygon map:", polygon.getMap());
        console.log("[Isochrone] Polygon paths:", polygon.getPath());
        console.log("[Isochrone] Polygon paths length:", polygon.getPath().getLength());
        
        // Double-check polygon is on the map (defensive programming)
        if (!polygon.getMap()) {
            console.warn("[Isochrone] WARNING: Polygon map is null, re-attaching...");
            polygon.setMap(map);
        }
        
        // Verify polygon is actually visible
        if (polygon.getMap() !== map) {
            console.error("[Isochrone] ERROR: Polygon map mismatch!");
            polygon.setMap(map);
        }
        
        // Ensure polygon is visible by checking after a brief delay
        setTimeout(() => {
            if (activeIsochronePolygon === polygon && !polygon.getMap()) {
                console.warn("[Isochrone] Polygon lost map reference, re-attaching...");
                polygon.setMap(map);
            }
        }, 50);
        
        console.log("[Isochrone] Polygon successfully added to map");
        showToast(`${minutes}-minute isochrone generated`, "success");
        
        // No auto-zoom - map view remains unchanged per requirements
        
    } catch (error) {
        console.error("[Isochrone] Error generating isochrone:", error);
        console.error("[Isochrone] Error stack:", error.stack);
        showToast("Error generating isochrone: " + error.message, "error");
    } finally {
        // Always reset the flag, even on error
        isGeneratingIsochrone = false;
    }
}

/**
 * Clear SAM project markers
 */
function clearSAMMarkers() {
    samMarkers.forEach(({ marker, infoWindow }) => {
        marker.setMap(null);
        infoWindow.close();
    });
    samMarkers = [];
}

/**
 * Clear places markers
 */
function clearPlacesMarkers() {
    placesMarkers.forEach(({ marker, infoWindow }) => {
        marker.setMap(null);
        infoWindow.close();
    });
    placesMarkers = [];
}

// Note: window.generateIsochroneFromInfo is now defined at the top of the file
// to ensure it's available when InfoWindows are created

/**
 * Toast-style error handling and notifications
 * Shows temporary notifications in top-right corner
 */
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.classList.add("show");
    }, 10);
    
    // Remove after delay
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return "N/A";
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize map when Google Maps API loads
 * This function is called by the Google Maps API callback when using async loading
 * Define it early to ensure it's available when the callback fires
 */
window.initMap = function() {
    if (typeof google !== "undefined" && google.maps) {
        initializeMap();
    } else {
        showToast("Error: Google Maps API failed to load", "error");
    }
};

// Fallback for synchronous loading (if async callback doesn't fire)
// Wait a bit to ensure scripts are loaded
if (typeof google !== "undefined" && google.maps) {
    // Use setTimeout to ensure app.js is fully loaded
    setTimeout(function() {
        if (typeof initializeMap === "function") {
            window.initMap();
        }
    }, 100);
}
