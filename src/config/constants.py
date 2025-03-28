import os
import time
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App configuration
APP_TITLE = "AI Application Generator"
APP_DESCRIPTION = "Generate complete, functional applications from text descriptions"

# API configuration
USE_OPENROUTER = True
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_SITE_URL = "https://ai-application-generator.com"
OPENROUTER_SITE_NAME = "AI Application Generator"
OPENROUTER_MODEL = "google/gemini-2.5-pro-exp-03-25:free"
# OPENROUTER_MODEL = "google/gemini-2.5-pro-exp-03-25:free"

# Free model rate limiting
FREE_MODEL_SUFFIX = ":free"
FREE_MODEL_BASE_DELAY = 11  # minimum seconds to wait between API calls for free models
MIN_RETRY_DELAY = 20  # minimum seconds to wait when hitting a rate limit
last_successful_response_time = 0  # track the last SUCCESSFUL API response time

def is_free_model(model_name):
    """Check if the model is a free tier model"""
    return model_name and isinstance(model_name, str) and model_name.endswith(FREE_MODEL_SUFFIX)

def apply_rate_limit_if_needed(model_name):
    """Apply rate limiting delay if using a free model before making an API call"""
    global last_successful_response_time
    
    if is_free_model(model_name):
        # Calculate time since last successful response
        current_time = time.time()
        elapsed_time = current_time - last_successful_response_time
        
        # If less than FREE_MODEL_BASE_DELAY seconds have passed, wait
        if elapsed_time < FREE_MODEL_BASE_DELAY and last_successful_response_time > 0:
            wait_time = FREE_MODEL_BASE_DELAY - elapsed_time
            print(f"Rate limiting: Waiting {wait_time:.2f} seconds for free model {model_name}")
            time.sleep(wait_time)

def update_last_successful_response_time():
    """Mark the current time as the last successful response time"""
    global last_successful_response_time
    last_successful_response_time = time.time()

def extract_retry_delay_from_error(error_data):
    """
    Extract the suggested retry delay from the error response if available
    
    Args:
        error_data: The error data from the API response
        
    Returns:
        int: The suggested retry delay in seconds, or MIN_RETRY_DELAY if not found
    """
    try:
        if isinstance(error_data, dict) and 'error' in error_data:
            error_raw = error_data.get('metadata', {}).get('raw', '')
            
            # Try to find retryDelay in the error message
            retry_delay_match = re.search(r'"retryDelay":\s*"(\d+)s"', error_raw)
            if retry_delay_match:
                suggested_delay = int(retry_delay_match.group(1))
                return max(suggested_delay, MIN_RETRY_DELAY)
        
        # Default case if we couldn't extract a delay
        return MIN_RETRY_DELAY
    except Exception as e:
        print(f"Error extracting retry delay: {str(e)}")
        return MIN_RETRY_DELAY

# OpenAI fallback configuration
OPENAI_MODEL = "gpt-4o-mini"

# Generation settings
DEFAULT_TEMPERATURE = 0.4
CREATIVE_TEMPERATURE = 0.7
PRECISE_TEMPERATURE = 0.3

# Generation phases
GENERATION_PHASES = [
    "Analyzing requirements",
    "Designing architecture",
    "Creating element dictionary",
    "Creating file structure",
    "Generating frontend code",
    "Generating backend code",
    "Enhancing code quality",
    "Generating configuration files",
    "Finalizing project files",
    "Creating documentation"
]

# File generation defaults
DEFAULT_OUTPUT_DIR = "./generated_app"
README_TEMPLATE = """
# {app_name}

{app_description}

## Features
{features}

## Installation
{installation}

## Usage
{usage}

## Project Structure
{structure}

## License
This project is open source and available under the MIT License.
"""