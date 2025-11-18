"""
Configuration module for Site Scout Lite.
Loads environment variables from .env file and exports constants.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
# This will look for .env in the current directory and parent directories
load_dotenv()

# API Keys - loaded from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
SAM_API_KEY = os.getenv("SAM_API_KEY", "")
TRAVELTIME_API_KEY = os.getenv("TRAVELTIME_API_KEY", "")
TRAVELTIME_APP_ID = os.getenv("TRAVELTIME_APP_ID", "")

# API Base URLs
SAM_BASE_URL = "https://api.sam.gov/opportunities/v2/search"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# NAICS codes for filtering SAM.gov opportunities
# These represent:
# - 327300: Cement Manufacturing
# - 327320: Ready-Mix Concrete Manufacturing
# - 238110: Poured Concrete Foundation and Structure Contractors
NAICS_CODES = ["327300", "327320", "238110"]

# State filter - Virginia only
# All SAM.gov results must be filtered to Virginia state
STATE_FILTER = "VA"

# Logging setup
logger = logging.getLogger(__name__)

# Warning if SAM_API_KEY is missing (non-blocking)
if not SAM_API_KEY:
    logger.warning("SAM_API_KEY is not set. Live SAM.gov calls will not work.")
