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
        let apiUrl = "/api/projects";
        const params = new URLSearchParams();
        
        if (searchQuery) {
            params.append("q", searchQuery);
            params.append("search_type", searchType);
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
        
        // Add markers for each project
        projects.forEach(project => {
            if (project.lat && project.lng) {
                addSAMMarker(project);
            }
        });
        
        const successMsg = searchQuery
            ? `Found ${projects.length} project(s) for ${searchTypeLabel} "${searchQuery}"`
            : `Loaded ${projects.length} projects`;
        showToast(successMsg, "success");
        
    } catch (error) {
        console.error("Error loading SAM projects:", error);
        showToast("Error loading projects: " + error.message, "error");
    }
}

/**
 * Add a SAM project marker to the map
 */
function addSAMMarker(project) {
    const marker = new google.maps.Marker({
        position: { lat: project.lat, lng: project.lng },
        map: map,
        title: project.title || "SAM Project",
        icon: {
            url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png",
            scaledSize: new google.maps.Size(32, 32)
        }
    });
    
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
    
    // Use inline onclick handler for InfoWindow compatibility
    const lat = project.lat;
    const lng = project.lng;
    
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
            <div class="info-field">
                <span class="info-label">Est. award:</span>
                <span class="info-value">${formatCurrency(project.estimated_award_amount)}</span>
            </div>
            ${project.ui_link ? `
                <div class="info-link">
                    <a href="${escapeHtml(project.ui_link)}" target="_blank">View on SAM.gov</a>
                </div>
            ` : ''}
            <button class="btn-isochrone" onclick="window.generateIsochroneFromInfo(${lat}, ${lng})">
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
        
        // Add markers for each place
        places.forEach(place => {
            if (place.lat && place.lng) {
                addPlaceMarker(place);
            }
        });
        
        showToast(`Found ${places.length} places`, "success");
        
        // No auto-zoom - map view remains unchanged per requirements
        
    } catch (error) {
        console.error("Error searching places:", error);
        showToast("Error searching places: " + error.message, "error");
    }
}

/**
 * Add a place marker to the map
 */
function addPlaceMarker(place) {
    const marker = new google.maps.Marker({
        position: { lat: place.lat, lng: place.lng },
        map: map,
        title: place.name || "Place",
        icon: {
            url: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
            scaledSize: new google.maps.Size(32, 32)
        }
    });
    
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
    // Use inline onclick handler for InfoWindow compatibility
    const lat = place.lat;
    const lng = place.lng;
    
    return `
        <div class="info-card">
            <h3 class="info-title">${escapeHtml(place.name || "Place")}</h3>
            <div class="info-field">
                <span class="info-label">Address:</span>
                <span class="info-value">${escapeHtml(place.address || "N/A")}</span>
            </div>
            <button class="btn-isochrone" onclick="window.generateIsochroneFromInfo(${lat}, ${lng})">
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
    try {
        const minutes = parseInt(document.getElementById("driveTimeSelect").value);
        
        console.log(`[Isochrone] Starting generation for ${minutes} minutes at (${lat}, ${lng})`);
        showToast(`Generating ${minutes}-minute isochrone...`, "info");
        
        // Support mock mode via URL parameter (for testing: add &mock=true to URL)
        const urlParams = new URLSearchParams(window.location.search);
        const useMock = urlParams.get('mock') === 'true';
        const apiUrl = `/api/isochrones?lat=${lat}&lng=${lng}&minutes=${minutes}${useMock ? '&mock=true' : ''}`;
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
        
        // Clear previous isochrone
        if (activeIsochronePolygon) {
            console.log("[Isochrone] Clearing previous polygon");
            activeIsochronePolygon.setMap(null);
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
            map: map
        });
        
        console.log("[Isochrone] Polygon created:", polygon);
        console.log("[Isochrone] Polygon map:", polygon.getMap());
        console.log("[Isochrone] Polygon paths:", polygon.getPath());
        console.log("[Isochrone] Polygon paths length:", polygon.getPath().getLength());
        
        activeIsochronePolygon = polygon;
        
        // Verify polygon is on the map
        if (!polygon.getMap()) {
            console.error("[Isochrone] WARNING: Polygon was created but map is null!");
            polygon.setMap(map);
        }
        
        console.log("[Isochrone] Polygon successfully added to map");
        showToast(`${minutes}-minute isochrone generated`, "success");
        
        // No auto-zoom - map view remains unchanged per requirements
        
    } catch (error) {
        console.error("[Isochrone] Error generating isochrone:", error);
        console.error("[Isochrone] Error stack:", error.stack);
        showToast("Error generating isochrone: " + error.message, "error");
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

/**
 * Global function to be called from InfoWindow buttons
 * InfoWindows render in a separate context, so we need a global function
 */
window.generateIsochroneFromInfo = function(lat, lng) {
    generateIsochrone(lat, lng);
};

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
 */
window.initMap = function() {
    if (typeof google !== "undefined" && google.maps) {
        initializeMap();
    } else {
        showToast("Error: Google Maps API failed to load", "error");
    }
};

// Fallback for synchronous loading (if async callback doesn't fire)
if (typeof google !== "undefined" && google.maps) {
    window.initMap();
}
