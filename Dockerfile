# Site Scout Lite Dockerfile
# Containerized FastAPI application with static frontend

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
# python:3.11-slim includes most needed packages
# Clean up apt cache to reduce image size
RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
# Maintain directory structure: src/backend/
COPY src/backend/ ./src/backend/

# Copy frontend files
# Maintain directory structure: src/frontend/
COPY src/frontend/ ./src/frontend/

# Set Python path so imports work correctly
ENV PYTHONPATH=/app/src/backend

# Set working directory to backend for running the app
WORKDIR /app/src/backend

# Expose port 8000
EXPOSE 8000

# Run the FastAPI application with uvicorn
# --host 0.0.0.0 allows external connections
# --port overrides the default port for Azure
CMD ["sh", "-c", "uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT}"]
