import json
import logging
from typing import Dict, Any, Optional
from src.config import TEST_GENERATOR_PROMPT, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def generate_tests(api_client, file_path: str, code_content: str, project_context: Dict[str, Any]) -> Optional[str]:
    """Generate test code for a given file"""
    context = {
        "file_path": file_path,
        "code_content": code_content,
        "project_context": project_context
    }
    
    return api_client.call_agent(
        TEST_GENERATOR_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_DEFAULT,
        agent_type="test"
    )
