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
Utility functions for checking OpenRouter model capabilities using live API data.
This replaces the hardcoded model_capabilities.py approach with dynamic API-based detection.
"""

import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Cache for model data to avoid repeated API calls
_model_cache = None
_model_data_by_id = None

def _fetch_model_data():
    """Fetch model data from OpenRouter API and cache it."""
    global _model_cache, _model_data_by_id
    
    if _model_cache is not None:
        return _model_cache
    
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json().get("data", [])
        _model_cache = data
        
        # Create a lookup dictionary by model ID for faster access
        _model_data_by_id = {model.get("id", ""): model for model in data}
        
        logger.info(f"Fetched {len(data)} models from OpenRouter API")
        return data
        
    except Exception as e:
        logger.warning(f"Failed to fetch model data from OpenRouter API: {e}")
        return []

def model_supports_tools_api(model_name: str) -> bool:
    """
    Check if a model supports function calling / tools using live OpenRouter API data.
    
    Args:
        model_name (str): The model name/ID to check
        
    Returns:
        bool: True if the model supports tools, False otherwise
    """
    # Ensure model data is loaded
    _fetch_model_data()
    
    if _model_data_by_id is None:
        logger.warning("No model data available, falling back to conservative approach")
        return False
    
    # Direct lookup by model ID
    model_data = _model_data_by_id.get(model_name)
    
    if model_data:
        supported_parameters = model_data.get("supported_parameters", [])
        has_tools = any("tool" in param for param in supported_parameters)
        
        logger.debug(f"Model {model_name}: tools={has_tools}, params={supported_parameters}")
        return has_tools
    
    # If not found by exact ID, try partial matching (for model variants)
    model_lower = model_name.lower()
    for model_id, model_info in _model_data_by_id.items():
        if model_lower in model_id.lower() or model_id.lower() in model_lower:
            supported_parameters = model_info.get("supported_parameters", [])
            has_tools = any("tool" in param for param in supported_parameters)
            
            logger.debug(f"Model {model_name} matched {model_id}: tools={has_tools}")
            return has_tools
    
    # Model not found - conservative default
    logger.warning(f"Model {model_name} not found in OpenRouter API data, assuming no tool support")
    return False

def get_fallback_model_for_tools_api(original_model: str) -> str:
    """
    Get a fallback model that supports tools if the original doesn't, using live API data.
    
    Args:
        original_model (str): The original model that might not support tools
        
    Returns:
        str: A model that supports tools, preferably from the same provider
    """
    # Ensure model data is loaded
    _fetch_model_data()
    
    if _model_data_by_id is None:
        # Fallback to a known reliable model
        return "openai/gpt-4o-mini"
    
    original_lower = original_model.lower()
    provider = original_model.split("/")[0] if "/" in original_model else ""
    
    # Look for models from the same provider that support tools
    provider_models_with_tools = []
    all_models_with_tools = []
    
    for model_id, model_info in _model_data_by_id.items():
        supported_parameters = model_info.get("supported_parameters", [])
        has_tools = any("tool" in param for param in supported_parameters)
        
        if has_tools:
            all_models_with_tools.append(model_id)
            
            # Check if it's from the same provider
            if provider and model_id.startswith(provider + "/"):
                provider_models_with_tools.append(model_id)
    
    # Prefer models from the same provider
    if provider_models_with_tools:
        # Sort by preference (usually smaller/cheaper models first)
        if provider.lower() in ["openai"]:
            # For OpenAI, prefer gpt-4o-mini over gpt-4o for cost
            for model in ["openai/gpt-4o-mini", "openai/gpt-4o", "openai/gpt-4-turbo"]:
                if model in provider_models_with_tools:
                    return model
        elif provider.lower() in ["anthropic"]:
            # For Anthropic, prefer haiku for cost
            for model in ["anthropic/claude-3-haiku", "anthropic/claude-3-5-sonnet", "anthropic/claude-3-opus"]:
                if model in provider_models_with_tools:
                    return model
        elif provider.lower() in ["google"]:
            # For Google, prefer flash for cost
            for model in ["google/gemini-flash-1.5", "google/gemini-pro-1.5"]:
                if model in provider_models_with_tools:
                    return model
        
        # Fallback to first available from same provider
        return provider_models_with_tools[0]
    
    # No models from same provider, use a reliable default
    reliable_defaults = [
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku", 
        "google/gemini-flash-1.5"
    ]
    
    for default_model in reliable_defaults:
        if default_model in all_models_with_tools:
            return default_model
    
    # Ultimate fallback
    if all_models_with_tools:
        return all_models_with_tools[0]
    
    # If somehow no models support tools (shouldn't happen), return a known good model
    return "openai/gpt-4o-mini"

def get_model_info_api(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a model from OpenRouter API.
    
    Args:
        model_name (str): The model name/ID to look up
        
    Returns:
        Optional[Dict]: Model information dict or None if not found
    """
    _fetch_model_data()
    
    if _model_data_by_id is None:
        return None
    
    return _model_data_by_id.get(model_name)

def refresh_model_cache():
    """Force refresh of the model cache."""
    global _model_cache, _model_data_by_id
    _model_cache = None
    _model_data_by_id = None
    _fetch_model_data()

# For backward compatibility, provide aliases
model_supports_tools = model_supports_tools_api
get_fallback_model_for_tools = get_fallback_model_for_tools_api

if __name__ == "__main__":
    # Test the functions
    import sys
    logging.basicConfig(level=logging.INFO)
    
    test_models = [
        "openai/gpt-4o",
        "openai/gpt-4o-mini", 
        "openai/gpt-4.1-nano",
        "anthropic/claude-3-haiku",
        "google/gemini-flash-1.5",
        "meta-llama/llama-3-8b-instruct",
        "invalid/model-name"
    ]
    
    print("Testing model tool support detection:")
    for model in test_models:
        supports = model_supports_tools_api(model)
        print(f"  {model}: {'✅' if supports else '❌'}")
    
    print(f"\nTesting fallback model selection:")
    for model in test_models[:3]:
        fallback = get_fallback_model_for_tools_api(model)
        print(f"  {model} -> {fallback}")
