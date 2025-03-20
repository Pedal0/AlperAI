import json
import logging
from typing import Dict, Any, Optional

from src.config import REQUIREMENTS_ANALYZER_PROMPT, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def analyze_requirements(api_client, user_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Analyze user prompt to extract requirements
    
    Args:
        api_client: API client instance
        user_prompt: User's description of the desired application
        
    Returns:
        Requirements specification dictionary or None if analysis failed
    """
    response = api_client.call_agent(
        REQUIREMENTS_ANALYZER_PROMPT, 
        user_prompt, 
        max_tokens=MAX_TOKENS_DEFAULT
    )
    
    if not response:
        logger.error("No response received for requirements analysis")
        return None
        
    try:
        if "```json" in response or "```" in response:
            # Extract JSON from code blocks if present
            start = response.find("```json")
            if start != -1:
                start += 7  
            else:
                start = response.find("```")
                if start != -1:
                    start += 3  
            
            if start != -1:
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
                
        requirements = json.loads(response)
        
        if not isinstance(requirements, dict):
            logger.error(f"Requirements analysis returned invalid format: {type(requirements)}")
            return None
            
        logger.info("Requirements analysis successful")
        return requirements
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse requirements JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {response[:500]}")
        return None
