import json
import logging
from typing import Dict, Any, Optional
from src.config import (
    CODE_REVIEWER_PROMPT, 
    FILE_SIGNATURE_EXTRACTOR_PROMPT, 
    CROSS_FILE_REVIEWER_PROMPT,
    MAX_TOKENS_DEFAULT,
    MAX_TOKENS_LARGE
)

logger = logging.getLogger(__name__)

def review_code(api_client, file_path: str, code_content: str, file_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Review code quality for a file"""
    context = {
        "file_path": file_path,
        "code_content": code_content,
        "file_specification": file_spec
    }
    
    response = api_client.call_agent(
        CODE_REVIEWER_PROMPT, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_DEFAULT,
        agent_type="review"
    )
    return api_client._safe_parse_json(response)

def extract_file_signature(api_client, file_path: str, content: str) -> Dict[str, Any]:
    """Extract function and class signatures from a file"""
    context = {
        "file_path": file_path,
        "code_content": content
    }
    
    response = api_client.call_agent(
        FILE_SIGNATURE_EXTRACTOR_PROMPT,
        json.dumps(context), 
        max_tokens=MAX_TOKENS_DEFAULT,
        agent_type="review"
    )
    
    signature = api_client._safe_parse_json(response)
    
    if not signature:
        return {
            "file_path": file_path,
            "functions": [],
            "classes": [],
            "imports": []
        }
            
    return signature

def _extract_code_content(response: str, file_path: str) -> Optional[str]:
    """Extract code content from API response"""
    if "```" in response:
        start_markers = ["```python", "```javascript", "```java", "```typescript", "```"]
        for marker in start_markers:
            if marker in response:
                parts = response.split(marker, 1)
                if len(parts) > 1:
                    code_part = parts[1]
                    end_marker_pos = code_part.find("```")
                    if end_marker_pos != -1:
                        return code_part[:end_marker_pos].strip()
    
    if file_path in response:
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if file_path in line and i+1 < len(lines):
                return '\n'.join(lines[i+1:])
    
    return response

def cross_file_review(api_client, all_files: Dict[str, str], project_context: Dict[str, Any]) -> Dict[str, str]:
    """Review code across multiple files for consistency"""
    results = {}
    
    # Extract signatures from all files
    project_signatures = {}
    for path, content in all_files.items():
        project_signatures[path] = extract_file_signature(api_client, path, content)
    
    # Review each file against all signatures
    for file_path, content in all_files.items():
        context = {
            "file_to_review": file_path,
            "file_content": content,
            "project_signatures": project_signatures,
            "project_context": project_context
        }
        
        response = api_client.call_agent(
            CROSS_FILE_REVIEWER_PROMPT, 
            json.dumps(context), 
            max_tokens=MAX_TOKENS_LARGE,
            agent_type="review"
        )
        
        if response and response.strip() == "PARFAIT":
            results[file_path] = "PARFAIT"
        else:
            code_content = _extract_code_content(response, file_path)
            results[file_path] = code_content if code_content else response
                
    return results
