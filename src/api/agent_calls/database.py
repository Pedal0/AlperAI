import json
import logging
from typing import Dict, Any, Optional
from src.config import DATABASE_DESIGNER_PROMPT, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def design_database(api_client, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Design database schema based on requirements and architecture"""
    context = {
        "requirements": requirements_spec,
        "architecture": architecture
    }
    
    response = api_client.call_agent(
        DATABASE_DESIGNER_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_DEFAULT
    )
    return api_client._safe_parse_json(response)
