"""
Utility functions for loading and managing environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from src.config.constants import OPENROUTER_API_KEY_ENV

def load_env_vars():
    """
    Load environment variables from .env file if it exists.
    
    Returns:
        bool: True if .env was loaded, False otherwise
    """
    # Look for .env in the root directory
    root_dir = Path(__file__).resolve().parents[2]  # Go up 2 levels from utils
    env_path = root_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        return True
    return False

def get_openrouter_api_key():
    """
    Get the OpenRouter API key from environment variables.
    
    Returns:
        str: The API key or empty string if not found
    """
    # Try to load .env file if not already loaded
    load_env_vars()
    
    # Return the API key if it exists
    return os.environ.get(OPENROUTER_API_KEY_ENV, "")
