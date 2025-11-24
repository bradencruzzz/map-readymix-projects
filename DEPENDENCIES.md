# Dependencies Documentation - Site Scout Lite

**Status:** ✅ Verified Working  
**Last Updated:** November 24, 2025  
**Python Version:** 3.11+

---

## Table of Contents

1. [Core Dependencies](#core-dependencies)
2. [Development Dependencies](#development-dependencies)
3. [External APIs](#external-apis)
4. [Version History](#version-history)
5. [Security Updates](#security-updates)
6. [Dependency Management](#dependency-management)

---

## Core Dependencies

### Production Requirements

**File:** `requirements.txt`

```txt
fastapi==0.119.0
uvicorn[standard]==0.37.0
python-dotenv==1.1.1
requests==2.32.5
pytest==7.4.3
httpx==0.25.2
jinja2==3.1.2
```

### Detailed Breakdown

#### FastAPI (0.119.0)
**Purpose:** Web framework for building APIs

**Features Used:**
- REST endpoint routing (`@app.get`, `@app.post`)
- Query parameter validation
- Automatic OpenAPI documentation
- Pydantic integration for type checking
- CORS middleware
- Static file serving

**Why this version:**
- Stable release with all needed features
- Compatible with Python 3.11+
- Active maintenance and security updates

**Documentation:** https://fastapi.tiangolo.com/

---

#### Uvicorn (0.37.0) with [standard]
**Purpose:** ASGI server for FastAPI

**Features Used:**
- HTTP/1.1 and HTTP/2 support
- WebSocket support (via `[standard]` extras)
- Auto-reload in development mode
- Graceful shutdowns
- Performance optimizations

**Why this version:**
- Latest stable release
- Excellent performance
- Recommended by FastAPI team

**Standard extras include:**
- `websockets` - WebSocket support
- `httptools` - Fast HTTP parsing
- `uvloop` - Fast event loop (Linux/Mac only)

**Documentation:** https://www.uvicorn.org/

---

#### python-dotenv (1.1.1)
**Purpose:** Load environment variables from `.env` files

**Features Used:**
- `load_dotenv()` function
- Override support
- Path resolution
- Multiple `.env` file locations

**Why this version:**
- Latest stable release
- Bug fixes for path handling
- Windows compatibility improvements

**Documentation:** https://github.com/theskumar/python-dotenv

---

#### Requests (2.32.5)
**Purpose:** HTTP client for external API calls

**Features Used:**
- GET/POST requests to external APIs
- JSON encoding/decoding
- Timeout handling
- Error handling (`raise_for_status()`)
- Session management

**Used for:**
- Google Geocoding API
- Google Places API
- SAM.gov API
- TravelTime API

**Why this version:**
- Industry standard HTTP library
- Latest stable with security patches
- urllib3 2.0+ compatible

**Documentation:** https://requests.readthedocs.io/

---

#### pytest (7.4.3)
**Purpose:** Testing framework

**Features Used:**
- Test discovery and execution
- Fixtures for setup/teardown
- Parametrized tests
- Test coverage reporting (with pytest-cov)
- Mock support

**Test files:**
- `tests/test_health.py` - Health endpoint
- `tests/test_projects_mock.py` - SAM.gov pipeline
- `tests/test_isochrones_stub.py` - Isochrone generation

**Why this version:**
- Stable, mature testing framework
- Excellent plugin ecosystem
- Python 3.11+ support

**Documentation:** https://docs.pytest.org/

---

#### httpx (0.25.2)
**Purpose:** Async HTTP client for testing FastAPI endpoints

**Features Used:**
- Async/sync dual-mode client
- FastAPI test client integration
- Full HTTP/1.1 and HTTP/2 support
- Connection pooling

**Used for:**
- Testing API endpoints without running server
- Mock HTTP requests in tests

**Why this version:**
- FastAPI recommended test client
- Async support for future scalability
- Drop-in replacement for requests

**Documentation:** https://www.python-httpx.org/

---

#### Jinja2 (3.1.2)
**Purpose:** Template engine (used by FastAPI)

**Features Used:**
- HTML template rendering (if needed)
- String formatting
- Error pages
- API key injection in index.html

**Why this version:**
- Required by FastAPI
- Stable, secure release
- Python 3.11+ compatible

**Documentation:** https://jinja.palletsprojects.com/

---

## Development Dependencies

### Optional Tools (Not in requirements.txt)

#### Playwright
**Purpose:** Browser automation for E2E testing

**Installation:**
```bash
npm install -g playwright
playwright install
```

**Used for:**
- `test_isochrone_playwright.js` - Full integration test
- Audit testing and verification

**Documentation:** https://playwright.dev/

---

#### Black (Code Formatter)
**Purpose:** Python code formatting

**Installation:**
```bash
pip install black
```

**Usage:**
```bash
black src/
```

---

#### Flake8 (Linter)
**Purpose:** Code linting and style checking

**Installation:**
```bash
pip install flake8
```

**Usage:**
```bash
flake8 src/
```

---

## External APIs

### Required API Keys

#### Google Maps APIs
**Services:**
- Maps JavaScript API (frontend)
- Geocoding API (backend)
- Places API - Text Search (backend)

**Rate Limits:**
- Maps JS: Unlimited
- Geocoding: 50 requests/second
- Places: 100 requests/second

**Pricing:**
- Maps JS: $7 per 1000 loads
- Geocoding: $5 per 1000 requests
- Places: $17 per 1000 requests
- **Free tier:** $200/month credit

**Get Key:** https://console.cloud.google.com/

---

#### TravelTime API
**Service:** Time-map isochrones (v4)

**Rate Limits:**
- Free tier: 2,500 requests/month
- Rate limit: 10 requests/minute

**Pricing:**
- Free: $0 (2,500 req/month)
- Starter: $49/month (10,000 req)
- Professional: $249/month (100,000 req)

**Features Used:**
- POST `/v4/time-map` endpoint
- `arrival_searches` mode
- Driving transportation
- 30/45/60 minute travel times

**Get Key:** https://traveltime.com/

---

#### SAM.gov API (Optional)
**Service:** Federal contract opportunities (v2)

**Rate Limits:**
- 1,000 requests/day (free tier)
- 10 requests/second

**Pricing:**
- Free (with registration)

**Features Used:**
- `/opportunities/v2/search` endpoint
- NAICS code filtering
- Date range queries
- Keyword search

**Fallback:** Mock data in `src/backend/sample_sam.json`

**Get Key:** https://open.gsa.gov/api/get-opportunities-public-api/

---

## Version History

### Current Version (v1.0.0)

**Release Date:** November 24, 2025

**Dependencies:**
```txt
fastapi==0.119.0 (updated from 0.104.1)
uvicorn[standard]==0.37.0 (updated from 0.24.0)
python-dotenv==1.1.1 (updated from 1.0.0)
requests==2.32.5 (updated from 2.31.0)
pytest==7.4.3 (unchanged)
httpx==0.25.2 (unchanged)
jinja2==3.1.2 (unchanged)
```

**Changes:**
- ✅ Updated to latest stable versions
- ✅ Security patches applied
- ✅ Python 3.11+ compatibility verified
- ✅ All tests passing

---

### Previous Version

**Dependencies:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
requests==2.31.0
pytest==7.4.3
httpx==0.25.2
jinja2==3.1.2
```

---

## Security Updates

### CVE Tracking

**None reported** for current dependency versions.

### Security Best Practices

1. ✅ **Regular updates** - Dependencies updated November 24, 2025
2. ✅ **Version pinning** - Exact versions specified (==)
3. ✅ **No known vulnerabilities** - All packages scanned
4. ✅ **Minimal dependencies** - Only essential packages
5. ✅ **Security patches** - Latest stable releases used

### Vulnerability Scanning

```bash
# Install safety
pip install safety

# Check for vulnerabilities
safety check -r requirements.txt
```

### Update Schedule

- **Monthly:** Check for security updates
- **Quarterly:** Update to latest stable versions
- **Immediate:** Critical security patches

---

## Dependency Management

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### Update Dependencies

```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade fastapi

# Freeze new versions
pip freeze > requirements.txt
```

### Check Outdated Packages

```bash
# List outdated packages
pip list --outdated

# Detailed information
pip show fastapi
```

### Dependency Tree

```bash
# Install pipdeptree
pip install pipdeptree

# View dependency tree
pipdeptree

# View specific package
pipdeptree -p fastapi
```

**Output:**
```
fastapi==0.119.0
├── pydantic>=1.7.4,!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0
├── starlette>=0.37.2,<0.39.0
└── typing-extensions>=4.8.0
```

### Lock File (Optional)

For reproducible builds, consider using `pip-tools`:

```bash
# Install pip-tools
pip install pip-tools

# Create requirements.in
echo "fastapi" > requirements.in
echo "uvicorn[standard]" >> requirements.in

# Generate locked requirements.txt
pip-compile requirements.in

# Install from lock file
pip-sync requirements.txt
```

---

## Python Version Compatibility

### Supported Versions

- ✅ **Python 3.11** (recommended)
- ✅ **Python 3.12** (tested)
- ⚠️ **Python 3.10** (deprecated, use 3.11+)
- ❌ **Python 3.9 or below** (not supported)

### Version-Specific Notes

**Python 3.11:**
- Recommended for production
- Best performance
- All features supported
- Long-term support

**Python 3.12:**
- Works correctly
- Minor deprecation warning for `datetime.utcnow()`
- Update to `datetime.now(UTC)` for full compatibility

**Python 3.10:**
- Deprecated but works
- Upgrade recommended

---

## Docker Dependencies

### Base Image

```dockerfile
FROM python:3.11-slim
```

**Why python:3.11-slim:**
- ✅ Smaller image size (~150 MB base)
- ✅ Python 3.11 included
- ✅ Debian-based (apt-get support)
- ✅ Security updates
- ✅ Official Python image

### System Dependencies

None required beyond Python 3.11-slim base.

**Optional (for production):**
- `curl` - Health checks
- `postgresql-client` - If adding database

---

## Frontend Dependencies

### JavaScript Libraries

**Google Maps JavaScript API:**
- Version: Latest (CDN)
- Load method: Async callback
- URL: `https://maps.googleapis.com/maps/api/js`

**No build tools required:**
- ✅ Vanilla JavaScript (ES6+)
- ✅ No npm/webpack/babel
- ✅ No transpilation needed
- ✅ Direct browser execution

---

## Minimum System Requirements

### Development

- **CPU:** 2 cores
- **RAM:** 4 GB
- **Disk:** 2 GB free space
- **OS:** Windows 10+, macOS 10.15+, Linux (any modern distro)

### Production (Docker)

- **CPU:** 2 cores
- **RAM:** 1 GB minimum, 2 GB recommended
- **Disk:** 500 MB for image + logs
- **OS:** Any Docker-compatible OS

---

## Troubleshooting

### Common Issues

#### "Module not found" error

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

#### "SSL certificate verify failed"

```bash
# Update certifi
pip install --upgrade certifi

# Or disable SSL verification (not recommended)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

#### "Could not find a version that satisfies"

```bash
# Update pip
pip install --upgrade pip

# Try again
pip install -r requirements.txt
```

---

## References

### Official Documentation

- **FastAPI:** https://fastapi.tiangolo.com/
- **Uvicorn:** https://www.uvicorn.org/
- **Requests:** https://requests.readthedocs.io/
- **pytest:** https://docs.pytest.org/
- **httpx:** https://www.python-httpx.org/

### Security Resources

- **PyPI Advisory Database:** https://github.com/pypa/advisory-database
- **Safety CLI:** https://github.com/pyupio/safety
- **Snyk:** https://snyk.io/

### Community

- **FastAPI Discord:** https://discord.gg/fastapi
- **Python Packaging:** https://packaging.python.org/

---

**Last Updated:** November 24, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production Ready

