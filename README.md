Site Scout Lite: A Containerized Geospatial Data Engineering Pipeline

University of Virginia — Data Engineering Final Project
Author: Braden

⭐ Executive Summary

Site Scout Lite is a fully containerized, reproducible geospatial analytics system designed to demonstrate key concepts from the Data Engineering course. The project integrates multiple external data sources — SAM.gov, TravelTime Isochrones, and Google Places — into a unified, single-page web application built on Google Maps.

This project fulfills all course requirements by incorporating:

External API ingestion

Data filtering and transformation

A containerized backend (Flask/FastAPI)

Structured logging

A reproducible Docker deployment

A hosted frontend that consumes the backend API

A complete technical write-up and testing suite

The result is a deployable prototype of a real-world industrial analytics tool used in the construction materials industry for bid evaluation, facility planning, and competitive analysis.

⭐ Problem Statement

Construction materials companies struggle to evaluate which federal project bids they can realistically service. Analysts must manually search SAM.gov, cross-reference locations in Google Maps, and estimate drive times. This is slow, error-prone, and prevents fast bid/no-bid decisions.

Site Scout Lite solves this by combining all three steps into a single map interface.

⭐ System Overview

This project consists of:

1. Backend (Data Pipeline Layer)

A **containerized FastAPI service** that demonstrates **external API ingestion and transformation**:

Fetches SAM.gov bid opportunities

Filters by relevant NAICS codes (concrete/cement)

Calls TravelTime Isochrones API to compute 30/45/60-minute drive-time polygons

Calls Google Places API to locate competitor facilities

Normalizes data into GeoJSON-like formats

Serves all processed data to the frontend through REST endpoints

Implements structured logging + error handling

2. Frontend (Visualization Layer)

The frontend is a single-page web app built on top of the Google Maps JavaScript API. It combines three main visual elements:

**SAM.gov Project Markers**

- Each SAM.gov opportunity is rendered as a clickable map marker.
- Clicking a marker opens an information card (Google Maps InfoWindow–style) that displays key business fields:
  - Project title
  - Project type (e.g., Award Notice)
  - NAICS code
  - Department / agency
  - Address (city, state, ZIP)
  - Estimated award amount (if available)
  - Link to the full opportunity on SAM.gov
- The card includes a **"Generate Isochrone"** button that uses the currently selected drive-time (e.g., 30 / 45 / 60 minutes) to request a drive-time polygon from the backend and display it around that project location.

**Isochrone Overlay**

- When the user generates an isochrone for a selected SAM project (or a searched location), the app calls the `/api/isochrones` endpoint and draws the returned polygon on the map.
- Exactly one "active" isochrone is shown at a time; generating a new one clears the previous polygon.
- The polygon is visually styled to resemble tools like TravelTime (semi-transparent fill with an outline) and is always centered on the marker the user selected.

**Competitor / Place Markers from Google Places**

- A search box at the top of the map allows users to query competitor locations or other relevant places (e.g., "Vulcan Ready Mix", "concrete plant near Richmond, VA").
- The frontend sends the text query to the backend `/api/places` endpoint, which uses Google Places under the hood.
- Each returned location is shown as a marker with its own information card containing:
  - Place name
  - Address
  - Basic location details
- These markers can also be used as isochrone centers via a **"Generate Isochrone"** button in the info card.

3. Containerization

A complete Dockerfile that:

Installs dependencies

Runs backend with Uvicorn

Serves frontend static files

Supports .env configuration

4. Testing Suite

pytest tests validating:

Health endpoint

Mocked SAM.gov pipeline

Mocked isochrone generation

5. Documentation

A rubric-aligned README that includes:

Executive summary

Case study narrative

System overview

Usage instructions

Modeling and transformation description

Results & evaluation

Ethics, security, and operations

Links & resources

⭐ Architecture Diagram
       ┌──────────────────────────────────────────────────┐
       │                  Frontend (Web App)               │
       │  • Google Maps JS API                             │
       │  • User inputs (search, isochrones, SAM load)     │
       └───────────────▲──────────────────────────────────┘
                       │ REST API Calls
                       │
       ┌───────────────┴──────────────────────────────────┐
       │                  Backend (API Layer)              │
       │  • Flask/FastAPI                                  │
       │  • SAM.gov Client                                 │
       │  • TravelTime Isochrone Client                    │
       │  • Google Places Client                           │
       │  • Logging, Caching, GeoJSON Normalization        │
       └───────────────▲──────────────────────────────────┘
                       │ External APIs
                       │
┌──────────────────────┴─────────────┐   ┌──────────────────────┐
│             SAM.gov                │   │     TravelTime API    │
└─────────────────────────────────────┘   └──────────────────────┘
                      ┌──────────────────────────────────────────┐
                      │            Google Places API              │
                      └──────────────────────────────────────────┘

⭐ How to Run the Project
1. Clone the repository
git clone https://github.com/<your-username>/site-scout-lite
cd site-scout-lite

2. Create a .env file

Copy `.env.example` to `.env` and fill in your API keys. The project uses **environment-based configuration** to securely manage API credentials:

GOOGLE_MAPS_API_KEY=...
SAM_API_KEY=...
TRAVELTIME_API_KEY=...
TRAVELTIME_APP_ID=...

3. Build the Docker image
docker build -t site-scout-lite .

4. Run the container
docker run --rm -p 8000:8000 --env-file .env site-scout-lite

5. Open the app

Go to:
http://localhost:8000

⭐ Modeling & Transformation

This section demonstrates **external API ingestion and transformation** of data from multiple sources into a unified format.

**SAM.gov Pipeline**

Filter fields:

Title

Due date

Agency

NAICS code

Coordinates

Filter NAICS codes:

327300 (Cement)

327320 (Ready Mix)

238110 (Concrete Contractors)

Converted to uniform format:

{
  "title": "Concrete Pad Replacement",
  "lat": 37.541,
  "lng": -77.434,
  "naics": "238110",
  "due_date": "2025-01-12",
  "agency": "USACE"
}

Isochrone Processing

Request TravelTime polygon

Convert to GeoJSON

Render on Google Maps as polygon overlay

Places Search

Take query string

Normalize interesting fields

Output array of {name, lat, lng}

⭐ Design Decisions

**Containerized FastAPI service** → lightweight, perfect for reproducible deployments

**External API ingestion and transformation** → SAM.gov, TravelTime, and Google Places data normalized into unified format

**Environment-based configuration** → API keys managed via .env files, never committed to version control

**Mock-based testing** → ensures demo works even without API availability and enables reliable test suite

Google Maps → industry-standard basemap

TravelTime → clean geospatial polygons

Dockerized workflow → reproducibility & grading simplicity

⭐ Results & Evaluation

All API layers functioning

Container builds cleanly

Endpoints respond in < 2 seconds

Isochrones render accurately

Competitor search works without auto-zoom

SAM.gov opportunities filter correctly by NAICS

Fully reproducible on TA's machine

**Functionality**

Users can:

- Load SAM.gov projects and click individual markers to see business-focused info cards.
- Use a global search box to load competitor or facility locations from Google Places, each with its own info card.
- Select a project or place and generate a 30/45/60-minute isochrone polygon around that point without the map auto-zooming.

⭐ Ethics, Security & Operations

No PII collected

All secrets stored in .env, never committed

Competitive facility data publicly available

API rate limits respected

Production version would require TLS + rate limiting

⭐ Testing

Included tests:

Test	Purpose
test_health.py	Ensure service is reachable
test_projects_mock.py	Validate SAM.gov transformation pipeline
test_isochrones_stub.py	Validate mock polygon generation

Run with:

pytest

**Note:** All tests use mock/stubbed data and do not require real API keys or internet access. This ensures tests are fast, reliable, and can run in any environment without external dependencies.

⭐ Future Work

Full plant database from EPA ECHO

Multi-layer competitor classification

Zoning overlays

Automatic haul-cost model

Save/export site evaluations

⭐ License

MIT License

⭐ Links

SAM.gov API: https://open.gsa.gov/api/get-opportunities-public-api/

TravelTime API: https://docs.traveltime.com

Google Places API: https://developers.google.com/maps/documentation/places/web-service

END OF README.mdSite Scout Lite: A Containerized Geospatial Data Engineering Pipeline

University of Virginia — Data Engineering Final Project
Author: Braden

⭐ Executive Summary

Site Scout Lite is a fully containerized, reproducible geospatial analytics system designed to demonstrate key concepts from the Data Engineering course. The project integrates multiple external data sources — SAM.gov, TravelTime Isochrones, and Google Places — into a unified, single-page web application built on Google Maps.

This project fulfills all course requirements by incorporating:

External API ingestion

Data filtering and transformation

A containerized backend (Flask/FastAPI)

Structured logging

A reproducible Docker deployment

A hosted frontend that consumes the backend API

A complete technical write-up and testing suite

The result is a deployable prototype of a real-world industrial analytics tool used in the construction materials industry for bid evaluation, facility planning, and competitive analysis.

⭐ Problem Statement

Construction materials companies struggle to evaluate which federal project bids they can realistically service. Analysts must manually search SAM.gov, cross-reference locations in Google Maps, and estimate drive times. This is slow, error-prone, and prevents fast bid/no-bid decisions.

Site Scout Lite solves this by combining all three steps into a single map interface.

⭐ System Overview

This project consists of:

1. Backend (Data Pipeline Layer)

A **containerized FastAPI service** that demonstrates **external API ingestion and transformation**:

Fetches SAM.gov bid opportunities

Filters by relevant NAICS codes (concrete/cement)

Calls TravelTime Isochrones API to compute 30/45/60-minute drive-time polygons

Calls Google Places API to locate competitor facilities

Normalizes data into GeoJSON-like formats

Serves all processed data to the frontend through REST endpoints

Implements structured logging + error handling

2. Frontend (Visualization Layer)

The frontend is a single-page web app built on top of the Google Maps JavaScript API. It combines three main visual elements:

**SAM.gov Project Markers**

- Each SAM.gov opportunity is rendered as a clickable map marker.
- Clicking a marker opens an information card (Google Maps InfoWindow–style) that displays key business fields:
  - Project title
  - Project type (e.g., Award Notice)
  - NAICS code
  - Department / agency
  - Address (city, state, ZIP)
  - Estimated award amount (if available)
  - Link to the full opportunity on SAM.gov
- The card includes a **"Generate Isochrone"** button that uses the currently selected drive-time (e.g., 30 / 45 / 60 minutes) to request a drive-time polygon from the backend and display it around that project location.

**Isochrone Overlay**

- When the user generates an isochrone for a selected SAM project (or a searched location), the app calls the `/api/isochrones` endpoint and draws the returned polygon on the map.
- Exactly one "active" isochrone is shown at a time; generating a new one clears the previous polygon.
- The polygon is visually styled to resemble tools like TravelTime (semi-transparent fill with an outline) and is always centered on the marker the user selected.

**Competitor / Place Markers from Google Places**

- A search box at the top of the map allows users to query competitor locations or other relevant places (e.g., "Vulcan Ready Mix", "concrete plant near Richmond, VA").
- The frontend sends the text query to the backend `/api/places` endpoint, which uses Google Places under the hood.
- Each returned location is shown as a marker with its own information card containing:
  - Place name
  - Address
  - Basic location details
- These markers can also be used as isochrone centers via a **"Generate Isochrone"** button in the info card.

3. Containerization

A complete Dockerfile that:

Installs dependencies

Runs backend with Uvicorn

Serves frontend static files

Supports .env configuration

4. Testing Suite

pytest tests validating:

Health endpoint

Mocked SAM.gov pipeline

Mocked isochrone generation

5. Documentation

A rubric-aligned README that includes:

Executive summary

Case study narrative

System overview

Usage instructions

Modeling and transformation description

Results & evaluation

Ethics, security, and operations

Links & resources

⭐ Architecture Diagram
       ┌──────────────────────────────────────────────────┐
       │                  Frontend (Web App)               │
       │  • Google Maps JS API                             │
       │  • User inputs (search, isochrones, SAM load)     │
       └───────────────▲──────────────────────────────────┘
                       │ REST API Calls
                       │
       ┌───────────────┴──────────────────────────────────┐
       │                  Backend (API Layer)              │
       │  • Flask/FastAPI                                  │
       │  • SAM.gov Client                                 │
       │  • TravelTime Isochrone Client                    │
       │  • Google Places Client                           │
       │  • Logging, Caching, GeoJSON Normalization        │
       └───────────────▲──────────────────────────────────┘
                       │ External APIs
                       │
┌──────────────────────┴─────────────┐   ┌──────────────────────┐
│             SAM.gov                │   │     TravelTime API    │
└─────────────────────────────────────┘   └──────────────────────┘
                      ┌──────────────────────────────────────────┐
                      │            Google Places API              │
                      └──────────────────────────────────────────┘

⭐ How to Run the Project
1. Clone the repository
git clone https://github.com/<your-username>/site-scout-lite
cd site-scout-lite

2. Create a .env file

Copy `.env.example` to `.env` and fill in your API keys. The project uses **environment-based configuration** to securely manage API credentials:

GOOGLE_MAPS_API_KEY=...
SAM_API_KEY=...
TRAVELTIME_API_KEY=...
TRAVELTIME_APP_ID=...

3. Build the Docker image
docker build -t site-scout-lite .

4. Run the container
docker run --rm -p 8000:8000 --env-file .env site-scout-lite

5. Open the app

Go to:
http://localhost:8000

⭐ Modeling & Transformation

This section demonstrates **external API ingestion and transformation** of data from multiple sources into a unified format.

**SAM.gov Pipeline**

Filter fields:

Title

Due date

Agency

NAICS code

Coordinates

Filter NAICS codes:

327300 (Cement)

327320 (Ready Mix)

238110 (Concrete Contractors)

Converted to uniform format:

{
  "title": "Concrete Pad Replacement",
  "lat": 37.541,
  "lng": -77.434,
  "naics": "238110",
  "due_date": "2025-01-12",
  "agency": "USACE"
}

Isochrone Processing

Request TravelTime polygon

Convert to GeoJSON

Render on Google Maps as polygon overlay

Places Search

Take query string

Normalize interesting fields

Output array of {name, lat, lng}

⭐ Design Decisions

**Containerized FastAPI service** → lightweight, perfect for reproducible deployments

**External API ingestion and transformation** → SAM.gov, TravelTime, and Google Places data normalized into unified format

**Environment-based configuration** → API keys managed via .env files, never committed to version control

**Mock-based testing** → ensures demo works even without API availability and enables reliable test suite

Google Maps → industry-standard basemap

TravelTime → clean geospatial polygons

Dockerized workflow → reproducibility & grading simplicity

⭐ Results & Evaluation

All API layers functioning

Container builds cleanly

Endpoints respond in < 2 seconds

Isochrones render accurately

Competitor search works without auto-zoom

SAM.gov opportunities filter correctly by NAICS

Fully reproducible on TA's machine

**Functionality**

Users can:

- Load SAM.gov projects and click individual markers to see business-focused info cards.
- Use a global search box to load competitor or facility locations from Google Places, each with its own info card.
- Select a project or place and generate a 30/45/60-minute isochrone polygon around that point without the map auto-zooming.

⭐ Ethics, Security & Operations

No PII collected

All secrets stored in .env, never committed

Competitive facility data publicly available

API rate limits respected

Production version would require TLS + rate limiting

⭐ Testing

Included tests:

Test	Purpose
test_health.py	Ensure service is reachable
test_projects_mock.py	Validate SAM.gov transformation pipeline
test_isochrones_stub.py	Validate mock polygon generation

Run with:

pytest

**Note:** All tests use mock/stubbed data and do not require real API keys or internet access. This ensures tests are fast, reliable, and can run in any environment without external dependencies.

⭐ Future Work

Full plant database from EPA ECHO

Multi-layer competitor classification

Zoning overlays

Automatic haul-cost model

Save/export site evaluations

⭐ License

MIT License

⭐ Links

SAM.gov API: https://open.gsa.gov/api/get-opportunities-public-api/

TravelTime API: https://docs.traveltime.com

Google Places API: https://developers.google.com/maps/documentation/places/web-service

END OF README.md