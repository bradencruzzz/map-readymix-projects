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
function initMap() {
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
 */
async function loadSAMProjects() {
    try {
        showToast("Loading SAM projects...", "info");
        
        const response = await fetch("/api/projects");
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const projects = await response.json();
        
        if (!Array.isArray(projects) || projects.length === 0) {
            showToast("No projects found", "warning");
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
        
        showToast(`Loaded ${projects.length} projects`, "success");
        
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
        
        showToast(`Generating ${minutes}-minute isochrone...`, "info");
        
        const response = await fetch(
            `/api/isochrones?lat=${lat}&lng=${lng}&minutes=${minutes}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const geojson = await response.json();
        
        // Clear previous isochrone
        if (activeIsochronePolygon) {
            activeIsochronePolygon.setMap(null);
            activeIsochronePolygon = null;
        }
        
        // Convert GeoJSON coordinates to Google Maps format
        // GeoJSON uses [lng, lat], Google Maps uses {lat, lng}
        const coordinates = geojson.geometry.coordinates[0].map(coord => ({
            lat: coord[1],
            lng: coord[0]
        }));
        
        // Create polygon with TravelTime-like styling
        const polygon = new google.maps.Polygon({
            paths: coordinates,
            strokeColor: "#4285F4",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: "#4285F4",
            fillOpacity: 0.2,
            map: map
        });
        
        activeIsochronePolygon = polygon;
        
        showToast(`${minutes}-minute isochrone generated`, "success");
        
        // No auto-zoom - map view remains unchanged per requirements
        
    } catch (error) {
        console.error("Error generating isochrone:", error);
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
 */
if (typeof google !== "undefined" && google.maps) {
    initMap();
} else {
    // Wait for API to load
    window.addEventListener("load", () => {
        if (typeof google !== "undefined" && google.maps) {
            initMap();
        } else {
            showToast("Error: Google Maps API failed to load", "error");
        }
    });
}
