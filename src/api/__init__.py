# API integration package
from .openrouter import (
    generate_text,
    optimize_prompt,
    generate_project_structure,
    generate_element_dictionary,
    generate_file_content,
    generate_readme,
    clean_generated_content,
    extract_external_resources
)

from .prompts import SYSTEM_MESSAGES, PROMPTS, FALLBACKS
