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
Utility functions for loading prompts from JSON configuration files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

# Cache for loaded prompt files to avoid reading files multiple times
_prompt_cache: Dict[str, Dict[str, Any]] = {}

def get_prompts_config_path() -> Path:
    """Get the path to the prompts configuration directory."""
    return Path(__file__).parents[1] / 'config' / 'prompts'

def load_agent_prompts(agent_file: str) -> Optional[Dict[str, Any]]:
    """
    Load prompts configuration for a specific agent.
    
    Args:
        agent_file (str): Name of the agent file (without .json extension)
        
    Returns:
        Dict containing the agent prompts configuration, or None if failed
    """
    global _prompt_cache
    
    if agent_file in _prompt_cache:
        return _prompt_cache[agent_file]
    
    config_path = get_prompts_config_path() / f"{agent_file}.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Cache the loaded configuration
        _prompt_cache[agent_file] = config
        return config
        
    except FileNotFoundError:
        logging.error(f"Prompt configuration file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON in {config_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error loading prompts from {config_path}: {e}")
        return None

def get_agent_prompt(agent_file: str, prompt_key: str, **kwargs) -> Optional[str]:
    """
    Get a specific prompt from an agent configuration file.
    
    Args:
        agent_file (str): Name of the agent file (without .json extension)
        prompt_key (str): Key of the prompt within the prompts section
        **kwargs: Variables to format into the prompt template
        
    Returns:
        Formatted prompt string, or None if not found
    """
    config = load_agent_prompts(agent_file)
    if not config:
        return None
    
    prompts = config.get('prompts', {})
    if prompt_key not in prompts:
        logging.error(f"Prompt key '{prompt_key}' not found in {agent_file}.json")
        return None
    
    prompt_template = prompts[prompt_key]
    
    # Format the prompt with provided variables
    try:
        return prompt_template.format(**kwargs)
    except KeyError as e:
        logging.error(f"Missing variable {e} for prompt '{prompt_key}' in {agent_file}.json")
        return prompt_template  # Return unformatted template as fallback
    except Exception as e:
        logging.error(f"Error formatting prompt '{prompt_key}' in {agent_file}.json: {e}")
        return prompt_template

def get_system_prompt_with_best_practices(agent_file: str, prompt_key: str = "system_prompt_with_best_practices") -> str:
    """
    Get a system prompt with best practices loaded from best_system_prompts.json.
    
    Args:
        agent_file (str): Name of the agent file (without .json extension)
        prompt_key (str): Key of the prompt within the prompts section
        
    Returns:
        System prompt with best practices, or fallback prompt if failed
    """    # Load best practices
    best_practices_path = Path(__file__).parents[1] / 'config' / 'best_system_prompts.json'
    best_practices = ""
    
    try:
        with open(best_practices_path, 'r', encoding='utf-8') as f:
            best_prompts_list = json.load(f)
        best_practices = ''.join(f'- {item}\n' for item in best_prompts_list)
    except Exception as e:
        logging.warning(f"Could not load best practices: {e}")
        
    # Get the prompt template and format it
    prompt = get_agent_prompt(agent_file, prompt_key, best_practices=best_practices)
    
    if prompt:
        return prompt
    
    # Fallback system prompt
    fallback_prompt = get_agent_prompt(agent_file, "system_prompt_base")
    if fallback_prompt:
        return fallback_prompt
        
    # Ultimate fallback
    return "You are an AI assistant. Follow best practices for your assigned task."

def clear_prompt_cache():
    """Clear the prompt cache to force reloading of configuration files."""
    global _prompt_cache
    _prompt_cache.clear()
