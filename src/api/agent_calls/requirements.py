import logging
from typing import Dict, Any, Optional
from src.config import REQUIREMENTS_ANALYZER_PROMPT, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def analyze_requirements(api_client, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Analyze user requirements and return structured specification"""
    response = api_client.call_agent(
        REQUIREMENTS_ANALYZER_PROMPT, 
        user_prompt, 
        max_tokens=MAX_TOKENS_DEFAULT
    )
    return api_client._safe_parse_json(response)
