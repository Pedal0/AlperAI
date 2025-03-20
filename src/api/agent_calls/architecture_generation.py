import json
import logging
from typing import Dict, Any, Optional

from src.config import ARCHITECTURE_DESIGNER_PROMPT, MAX_TOKENS_LARGE

logger = logging.getLogger(__name__)

def generate_architecture(api_client, requirements_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate application architecture based on requirements specification
    
    Args:
        api_client: API client instance 
        requirements_spec: Requirements specification dictionary
        
    Returns:
        Architecture specification dictionary or None if generation failed
    """
    req_json = json.dumps(requirements_spec, indent=2)
    
    response = api_client.call_agent(
        ARCHITECTURE_DESIGNER_PROMPT, 
        req_json, 
        max_tokens=MAX_TOKENS_LARGE
    )
    
    # Parse JSON response
    if not response:
        logger.error("No response received for architecture design")
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
                
        architecture = json.loads(response)
        
        if not isinstance(architecture, dict):
            logger.error(f"Architecture design returned invalid format: {type(architecture)}")
            return None
            
        logger.info("Architecture design successful")
        return architecture
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse architecture JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {response[:500]}")
        return None
