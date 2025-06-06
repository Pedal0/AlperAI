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
Constants configuration module for the application.
Contains all global constants used across the application.
"""

# API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-pro-exp-03-25:free"  # Free tier model
RATE_LIMIT_DELAY_SECONDS = 30  # Delay for free models

# Environment variable names
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"  # Name of the env var for the API key

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