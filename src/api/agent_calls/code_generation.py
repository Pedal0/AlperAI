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
    
    file_path = file_spec.get('path', '')
    agent_type = "css" if file_path.endswith('.css') else "code"
    
    return api_client.call_agent(
        CODE_GENERATOR_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_LARGE,
        agent_type=agent_type
    )

def generate_project_file(api_client, file_type: str, project_context: Dict[str, Any], file_structure: List[str]) -> str:
    """Generate project configuration files like requirements.txt or package.json"""
    context = {
        "file_type": file_type,
        "project_context": project_context,
        "file_structure": file_structure
    }
    
    # Déterminer le type d'agent selon le fichier généré
    if file_type == "README.md":
        agent_type = "reformulation"
    else:
        agent_type = "code"
    
    response = api_client.call_agent(
        PROJECT_FILES_GENERATOR_PROMPT,
        json.dumps(context),
        max_tokens=MAX_TOKENS_DEFAULT,
        agent_type=agent_type
    )
    
    return response
