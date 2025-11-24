# Docker Deployment Guide - Site Scout Lite

**Status:** ✅ Production Ready  
**Last Updated:** November 24, 2025  
**Docker Version:** 20.10+  
**Docker Compose Version:** 3.8

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Quick Start](#quick-start)
4. [Docker Build Options](#docker-build-options)
5. [Docker Compose](#docker-compose)
6. [Container Management](#container-management)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required Software

- **Docker:** Version 20.10 or higher
- **Docker Compose:** Version 2.0 or higher (optional but recommended)
- **API Keys:** 
  - Google Maps API Key (required)
  - TravelTime API Key + App ID (required)
  - SAM.gov API Key (optional)

### Get API Keys

#### Google Maps API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the following APIs:
   - Maps JavaScript API
   - Geocoding API
   - Places API (Text Search)
3. Create credentials → API Key
4. Restrict the key (optional but recommended):
   - HTTP referrers for frontend
   - IP addresses for backend

#### TravelTime API Credentials
1. Sign up at [TravelTime](https://traveltime.com/)
2. Get your API Key and App ID from dashboard
3. Free tier: 2,500 requests/month

#### SAM.gov API Key (Optional)
1. Register at [SAM.gov](https://sam.gov/)
2. Request API key
3. App falls back to mock data if not provided

---

## Environment Setup

### Create `.env` File

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit with your keys
nano .env  # or use your favorite editor
```

**Required Variables:**

```env
# Google Maps (Required)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# TravelTime (Required for isochrones)
TRAVELTIME_API_KEY=your_traveltime_api_key_here
TRAVELTIME_APP_ID=your_traveltime_app_id_here

# SAM.gov (Optional - uses mock data if not provided)
SAM_API_KEY=your_sam_api_key_here
```

**Important:**
- ❌ No quotes around values
- ❌ No spaces around `=` sign
- ❌ Never commit `.env` to version control
- ✅ Use `.env.example` as template

---

## Quick Start

### Option 1: Docker Run (Simple)

```bash
# 1. Build the image
docker build -t sitescout-lite:latest .

# 2. Run the container
docker run -d \
  --name sitescout \
  -p 8000:8000 \
  --env-file .env \
  sitescout-lite:latest

# 3. View logs
docker logs -f sitescout

# 4. Access the app
# Open browser to: http://localhost:8000
```

### Option 2: Docker Compose (Recommended)

```bash
# 1. Start the application
docker-compose up -d

# 2. View logs
docker-compose logs -f

# 3. Access the app
# Open browser to: http://localhost:8000

# 4. Stop the application
docker-compose down
```

---

## Docker Build Options

### Standard Build

```bash
docker build -t sitescout-lite:latest .
```

### No Cache Build (Clean Build)

```bash
docker build --no-cache -t sitescout-lite:latest .
```

### Build with Custom Tag

```bash
docker build -t sitescout-lite:v1.0.0 .
```

### Multi-platform Build (ARM + x86)

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t sitescout-lite:latest \
  .
```

### Build with Build Args

```bash
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  -t sitescout-lite:latest \
  .
```

---

## Docker Compose

### Configuration

**`docker-compose.yml`** (included in project):

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sitescout-lite
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    environment:
      - PYTHONPATH=/app/src/backend
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/api/health').raise_for_status()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - sitescout-network

networks:
  sitescout-network:
    driver: bridge
```

### Common Commands

```bash
# Start in detached mode
docker-compose up -d

# Start in foreground (see logs live)
docker-compose up

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild and start
docker-compose up -d --build

# View logs
docker-compose logs

# Follow logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f app

# Restart service
docker-compose restart

# Check status
docker-compose ps

# Execute command in container
docker-compose exec app bash
```

### Development Mode (Hot Reload)

Edit `docker-compose.yml` to mount source code:

```yaml
services:
  app:
    volumes:
      - ./src:/app/src
      - ./requirements.txt:/app/requirements.txt
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

---

## Container Management

### Start/Stop Container

```bash
# Start existing container
docker start sitescout

# Stop running container
docker stop sitescout

# Restart container
docker restart sitescout

# Pause container
docker pause sitescout

# Unpause container
docker unpause sitescout
```

### View Container Information

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View container logs
docker logs sitescout

# Follow logs in real-time
docker logs -f sitescout

# View last 100 lines
docker logs --tail 100 sitescout

# View container details
docker inspect sitescout

# View container stats
docker stats sitescout

# View container processes
docker top sitescout
```

### Execute Commands in Container

```bash
# Interactive bash shell
docker exec -it sitescout bash

# Run single command
docker exec sitescout ls -la /app

# Check Python version
docker exec sitescout python --version

# Test health endpoint
docker exec sitescout curl http://localhost:8000/api/health
```

### Remove Container

```bash
# Stop and remove container
docker stop sitescout
docker rm sitescout

# Force remove running container
docker rm -f sitescout
```

### Image Management

```bash
# List images
docker images

# Remove image
docker rmi sitescout-lite:latest

# Remove all unused images
docker image prune

# Remove all unused images (including dangling)
docker image prune -a

# Tag image
docker tag sitescout-lite:latest sitescout-lite:v1.0.0

# Save image to file
docker save sitescout-lite:latest > sitescout-lite.tar

# Load image from file
docker load < sitescout-lite.tar
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs sitescout
```

**Common issues:**

1. **Port already in use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000  # Linux/Mac
   netstat -ano | findstr :8000  # Windows
   
   # Use different port
   docker run -p 8001:8000 ...
   ```

2. **Missing API keys:**
   ```bash
   # Check environment variables
   docker exec sitescout env | grep API
   
   # Verify .env file exists and has keys
   cat .env
   ```

3. **Permission issues:**
   ```bash
   # Run with elevated privileges (if needed)
   sudo docker run ...
   ```

### Container is Running But App Not Accessible

**Check container status:**
```bash
docker ps
docker logs sitescout
```

**Test health endpoint:**
```bash
curl http://localhost:8000/api/health
```

**Check network:**
```bash
# Test from inside container
docker exec sitescout curl http://localhost:8000/api/health

# Check port mapping
docker port sitescout
```

### Application Errors

**View detailed logs:**
```bash
docker logs -f --tail 100 sitescout
```

**Common issues:**

1. **API key errors:**
   ```
   ERROR: GOOGLE_MAPS_API_KEY is not set
   ```
   **Solution:** Check .env file, restart container

2. **TravelTime API errors:**
   ```
   ERROR: TravelTime API credentials not configured
   ```
   **Solution:** Add TRAVELTIME_API_KEY and TRAVELTIME_APP_ID

3. **Import errors:**
   ```
   ModuleNotFoundError: No module named 'fastapi'
   ```
   **Solution:** Rebuild image: `docker build --no-cache -t sitescout-lite .`

### Performance Issues

**Check resource usage:**
```bash
docker stats sitescout
```

**Increase resources:**
```bash
# Docker Desktop: Settings → Resources
# Linux: --memory and --cpus flags
docker run --memory="1g" --cpus="2" ...
```

---

## Production Deployment

### Production Dockerfile

For production, consider these optimizations:

```dockerfile
FROM python:3.11-slim

# Production settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/src/backend

# Production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Production Environment Variables

```env
# Production settings
ENVIRONMENT=production
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://yourdomain.com

# API keys (use secrets management)
GOOGLE_MAPS_API_KEY=${SECRET_GOOGLE_MAPS_KEY}
TRAVELTIME_API_KEY=${SECRET_TRAVELTIME_KEY}
TRAVELTIME_APP_ID=${SECRET_TRAVELTIME_APP_ID}
```

### Docker Compose Production

```yaml
version: '3.8'

services:
  app:
    image: sitescout-lite:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    secrets:
      - google_maps_key
      - traveltime_key
      - traveltime_app_id
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

secrets:
  google_maps_key:
    external: true
  traveltime_key:
    external: true
  traveltime_app_id:
    external: true
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS with Let's Encrypt

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

### Cloud Deployment

#### AWS ECS

```bash
# Build and push to ECR
aws ecr create-repository --repository-name sitescout-lite
docker tag sitescout-lite:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/sitescout-lite
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/sitescout-lite
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project-id>/sitescout-lite
gcloud run deploy sitescout-lite --image gcr.io/<project-id>/sitescout-lite --platform managed
```

#### Azure Container Instances

```bash
# Create container
az container create \
  --resource-group myResourceGroup \
  --name sitescout-lite \
  --image sitescout-lite:latest \
  --ports 8000 \
  --environment-variables GOOGLE_MAPS_API_KEY=<key>
```

---

## Monitoring & Logging

### Container Logs

```bash
# JSON logs
docker logs sitescout --format=json

# Follow logs with timestamps
docker logs -f --timestamps sitescout

# Export logs
docker logs sitescout > logs.txt
```

### Health Checks

```bash
# Manual health check
curl http://localhost:8000/api/health

# Automated monitoring
watch -n 5 'curl -s http://localhost:8000/api/health | jq'
```

### Metrics

```bash
# Real-time stats
docker stats sitescout

# Export metrics
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Best Practices

### Security

1. ✅ **Never commit `.env` file**
2. ✅ **Use Docker secrets in production**
3. ✅ **Run as non-root user**
4. ✅ **Scan images for vulnerabilities**
5. ✅ **Keep base images updated**

### Performance

1. ✅ **Use multi-stage builds**
2. ✅ **Minimize layer count**
3. ✅ **Use `.dockerignore`**
4. ✅ **Cache dependencies**
5. ✅ **Set resource limits**

### Reliability

1. ✅ **Implement health checks**
2. ✅ **Use restart policies**
3. ✅ **Configure logging**
4. ✅ **Monitor resource usage**
5. ✅ **Test disaster recovery**

---

## Quick Reference

### Docker Commands Cheat Sheet

```bash
# Build
docker build -t sitescout-lite .

# Run
docker run -d --name sitescout -p 8000:8000 --env-file .env sitescout-lite

# Stop/Start
docker stop sitescout
docker start sitescout

# Logs
docker logs -f sitescout

# Shell
docker exec -it sitescout bash

# Clean up
docker system prune -a
```

### Docker Compose Cheat Sheet

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Clean up
docker-compose down -v --rmi all
```

---

**Need Help?**  
- Check application logs: `docker logs sitescout`
- Review `README.md` for general setup
- See `LOCATION_PIPELINE_AUDIT.md` for technical details

**Last Updated:** November 24, 2025  
**Version:** 1.0.0

