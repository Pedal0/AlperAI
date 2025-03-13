import json
import logging
from typing import Dict, Any, Optional
from src.config import ARCHITECTURE_DESIGNER_PROMPT, MAX_TOKENS_LARGE

logger = logging.getLogger(__name__)

def design_architecture(api_client, requirements_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Design application architecture based on requirements"""
    req_json = json.dumps(requirements_spec, indent=2)
    response = api_client.call_agent(
        ARCHITECTURE_DESIGNER_PROMPT, 
        req_json, 
        max_tokens=MAX_TOKENS_LARGE,
        agent_type="architecture"
    )
    
    architecture = api_client._safe_parse_json(response)
    
    if architecture:
        logger.info("Architecture design successful")
        
        # Normalize Flask dependency name
        if 'dependencies' in architecture and isinstance(architecture['dependencies'], list):
            for i, dep in enumerate(architecture['dependencies']):
                if isinstance(dep, dict) and dep.get('name') == 'Flask':
                    architecture['dependencies'][i]['name'] = 'flask'
                elif isinstance(dep, str) and dep == 'Flask':
                    architecture['dependencies'][i] = 'flask'
    else:
        logger.error("Architecture design failed")
            
    return architecture
