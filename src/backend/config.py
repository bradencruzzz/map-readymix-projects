"""
Configuration module for Site Scout Lite.
Loads environment variables from .env file and exports constants.
"""
import os
import logging
from dotenv import load_dotenv

# Logging setup (must be before using logger)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# Try multiple locations to find .env file
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
current_working_dir = os.getcwd()

# List of potential .env file locations (in order of preference)
env_paths = [
    os.path.join(current_working_dir, ".env"),  # Current working directory
    os.path.join(project_root, ".env"),  # Project root (parent of src/backend)
    os.path.join(script_dir, ".env"),  # Backend directory
    os.path.join(os.path.dirname(project_root), ".env"),  # Parent of project root
]

# Also try the absolute path if we can determine the workspace root
# This handles cases where the working directory might be different
workspace_root = None
try:
    # Try to find the workspace root by looking for common project files
    check_dir = project_root
    max_depth = 5
    depth = 0
    while depth < max_depth and check_dir != os.path.dirname(check_dir):
        if os.path.exists(os.path.join(check_dir, "Dockerfile")) or \
           os.path.exists(os.path.join(check_dir, "README.md")):
            workspace_root = check_dir
            break
        check_dir = os.path.dirname(check_dir)
        depth += 1
    
    if workspace_root:
        workspace_env = os.path.join(workspace_root, ".env")
        if workspace_env not in env_paths:
            env_paths.insert(0, workspace_env)  # Add to front of list
except Exception as e:
    logger.debug(f"Could not determine workspace root: {e}")

# Log what we're checking
logger.info(f"Looking for .env file. Current working directory: {current_working_dir}")
logger.info(f"Project root (calculated): {project_root}")

# Try to load .env from the first location that exists
# IMPORTANT: Only load .env, never .env.example
env_loaded = False
for env_path in env_paths:
    normalized_path = os.path.normpath(os.path.abspath(env_path))
    # Explicitly check it's .env and not .env.example
    if normalized_path.endswith(".env.example"):
        logger.debug(f"  Skipping .env.example: {normalized_path}")
        continue
    if os.path.exists(normalized_path) and normalized_path.endswith(".env"):
        load_dotenv(normalized_path, override=True)
        logger.info(f"✓ Loaded .env from: {normalized_path}")
        env_loaded = True
        break
    else:
        logger.info(f"  Checked (not found): {normalized_path}")

# If still not found, try direct absolute path based on workspace
if not env_loaded:
    # Try the workspace path directly (for Windows OneDrive paths)
    workspace_env_direct = os.path.normpath(os.path.join(project_root, ".env"))
    # Make sure it's .env and not .env.example
    if os.path.exists(workspace_env_direct) and workspace_env_direct.endswith(".env") and not workspace_env_direct.endswith(".env.example"):
        load_dotenv(workspace_env_direct, override=True)
        logger.info(f"✓ Loaded .env from direct path: {workspace_env_direct}")
        env_loaded = True

# If no .env file found in specific locations, try default behavior
# But explicitly look for .env, not .env.example
if not env_loaded:
    # Try to find .env in current directory and parent directories
    # But skip .env.example
    check_dir = current_working_dir
    max_depth = 10
    depth = 0
    while depth < max_depth and check_dir != os.path.dirname(check_dir):
        env_file = os.path.join(check_dir, ".env")
        env_example = os.path.join(check_dir, ".env.example")
        
        # Only load if .env exists and .env.example doesn't override it
        if os.path.exists(env_file) and env_file != env_example:
            load_dotenv(env_file, override=True)
            logger.info(f"✓ Loaded .env using default search from: {env_file}")
            env_loaded = True
            break
        check_dir = os.path.dirname(check_dir)
        depth += 1
    
    if not env_loaded:
        logger.warning(f"⚠ No .env file found. Checked locations:")
        for env_path in env_paths:
            normalized_path = os.path.normpath(env_path)
            exists = os.path.exists(normalized_path) and not normalized_path.endswith(".env.example")
            logger.warning(f"  {'✓' if exists else '✗'} {normalized_path}")
        logger.warning(f"  Current working directory: {current_working_dir}")
        logger.warning(f"  Project root: {project_root}")
        if workspace_root:
            logger.warning(f"  Workspace root: {workspace_root}")
        logger.warning("  Make sure .env file (NOT .env.example) exists in the project root or current working directory.")
        logger.warning("  .env.example is a template - copy it to .env and fill in your actual API keys.")

# API Keys - loaded from environment variables
# No fallback values - keys must be set in .env file or environment variables
# This ensures it works both locally (from .env) and in Docker (from --env-file)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SAM_API_KEY = os.getenv("SAM_API_KEY")
TRAVELTIME_API_KEY = os.getenv("TRAVELTIME_API_KEY")
TRAVELTIME_APP_ID = os.getenv("TRAVELTIME_APP_ID")

# Debug: Log what was loaded (without showing actual keys)
if env_loaded:
    logger.info("Environment variables loaded. Checking for API keys...")
    found_keys = []
    if GOOGLE_MAPS_API_KEY:
        found_keys.append("GOOGLE_MAPS_API_KEY")
    if SAM_API_KEY:
        found_keys.append("SAM_API_KEY")
    if TRAVELTIME_API_KEY:
        found_keys.append("TRAVELTIME_API_KEY")
    if TRAVELTIME_APP_ID:
        found_keys.append("TRAVELTIME_APP_ID")
    
    if found_keys:
        logger.info(f"Found {len(found_keys)} API key(s) in environment: {', '.join(found_keys)}")
    else:
        logger.warning("⚠ .env file was loaded but no API keys were found.")
        logger.warning("  This might mean:")
        logger.warning("  1. You're loading .env.example instead of .env")
        logger.warning("  2. Your .env file is empty or has incorrect format")
        logger.warning("  3. Your .env file has keys but they're commented out or have spaces")
        logger.warning("  Make sure your .env file (NOT .env.example) contains:")
        logger.warning("  GOOGLE_MAPS_API_KEY=your_actual_key_here")
        logger.warning("  SAM_API_KEY=your_actual_key_here")
        logger.warning("  TRAVELTIME_API_KEY=your_actual_key_here")
        logger.warning("  TRAVELTIME_APP_ID=your_actual_app_id_here")
        logger.warning("  (No quotes, no spaces around =, one per line)")

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

# Validate API keys and log status (no fallback values - keys must be set)
if GOOGLE_MAPS_API_KEY:
    logger.info("✓ GOOGLE_MAPS_API_KEY is set")
else:
    logger.warning("GOOGLE_MAPS_API_KEY is not set. Google Maps will not work.")
    logger.warning("  Make sure GOOGLE_MAPS_API_KEY is in your .env file or set as an environment variable.")

if SAM_API_KEY:
    logger.info("✓ SAM_API_KEY is set")
else:
    logger.warning("SAM_API_KEY is not set. Live SAM.gov calls will not work.")
    logger.warning("  Make sure SAM_API_KEY is in your .env file or set as an environment variable.")

if TRAVELTIME_API_KEY and TRAVELTIME_APP_ID:
    logger.info("✓ TravelTime credentials are set")
else:
    logger.warning("TRAVELTIME_API_KEY or TRAVELTIME_APP_ID is not set. Live isochrone generation will not work.")
    logger.warning("  Make sure both TRAVELTIME_API_KEY and TRAVELTIME_APP_ID are in your .env file or set as environment variables.")
