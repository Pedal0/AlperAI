# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

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

def is_vercel_environment():
    """
    Détecte si l'application est déployée sur Vercel.
    
    Returns:
        bool: True si l'application est sur Vercel, False sinon
    """
    # Vercel définit ces variables d'environnement
    vercel_env = os.environ.get('VERCEL', '')
    vercel_region = os.environ.get('VERCEL_REGION', '')
    
    # Si au moins une de ces variables existe, nous sommes sur Vercel
    return bool(vercel_env or vercel_region)
