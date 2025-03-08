import json
import logging
from typing import Dict, Any, List, Optional
from src.config import CODE_GENERATOR_PROMPT, PROJECT_FILES_GENERATOR_PROMPT, MAX_TOKENS_LARGE, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def generate_code(api_client, file_spec: Dict[str, Any], project_context: Dict[str, Any]) -> Optional[str]:
    """Generate code for a single file"""
    context = {
        "file_specification": file_spec,
        "project_context": project_context
    }
    
    return api_client.call_agent(
        CODE_GENERATOR_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_LARGE
    )

def generate_project_file(api_client, file_type: str, project_context: Dict[str, Any], file_structure: List[str]) -> str:
    """Generate project configuration files like requirements.txt or package.json"""
    context = {
        "file_type": file_type,
        "project_context": project_context,
        "file_structure": file_structure
    }
    
    response = api_client.call_agent(
        PROJECT_FILES_GENERATOR_PROMPT,
        json.dumps(context),
        max_tokens=MAX_TOKENS_DEFAULT
    )
    
    return response
