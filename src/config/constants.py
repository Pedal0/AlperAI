"""
Constants configuration module for the application.
Contains all global constants used across the application.
"""

# API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-pro-exp-03-25:free"  # Free tier model
RATE_LIMIT_DELAY_SECONDS = 30  # Delay for free models

# OpenAI fallback configuration (if needed)
USE_OPENROUTER = True  # Toggle between OpenRouter and OpenAI
API_MODEL = "gpt-4o-mini"  # Default OpenAI model if OpenRouter not used

# Model-specific configurations
OPENROUTER_MODEL = DEFAULT_MODEL

# Temperature settings
STRUCTURE_TEMPERATURE = 0.6  # More structured output
CODE_TEMPERATURE = 0.4  # Less creative, more precise code generation

# Other constants
MAX_RETRIES = 2  # Maximum number of API call retries
