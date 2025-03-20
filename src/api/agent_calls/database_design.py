import json
import logging
from typing import Dict, Any, Optional

from src.config import DATABASE_DESIGNER_PROMPT, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def design_database(api_client, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Design database schema based on requirements and architecture
    
    Args:
        api_client: API client instance
        requirements_spec: Requirements specification dictionary
        architecture: Architecture specification dictionary
        
    Returns:
        Database schema dictionary or None if design failed
    """
    context = {
        "requirements": requirements_spec,
        "architecture": architecture
    }
    
    response = api_client.call_agent(
        DATABASE_DESIGNER_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_DEFAULT
    )
    
    if not response:
        logger.error("No response received for database design")
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
                
        database_schema = json.loads(response)
        
        if not isinstance(database_schema, dict):
            logger.error(f"Database design returned invalid format: {type(database_schema)}")
            return None
            
        logger.info("Database design successful")
        return database_schema
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse database schema JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {response[:500]}")
        return None
