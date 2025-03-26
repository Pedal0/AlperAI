import os
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
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

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