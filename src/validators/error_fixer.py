import os
import json
import logging
import re
from typing import Dict, Any, Optional

from src.config import APP_FIXER_PROMPT

logger = logging.getLogger(__name__)

def identify_error_file(app_path: str, error_info: Dict[str, Any]) -> Optional[str]:
    """Identify the file causing an error based on error messages"""
    if "stderr" not in error_info:
        return None
        
    error_text = error_info.get("stderr", "") + error_info.get("stdout", "")
    
    lines = error_text.split('\n')
    for line in lines:
        if "File " in line and ".py" in line:
            parts = line.split('File "', 1)
            if len(parts) > 1:
                file_path = parts[1].split('"', 1)[0]
                
                if not os.path.isabs(file_path):
                    file_path = os.path.join(app_path, file_path)
                    
                if os.path.exists(file_path):
                    return file_path
        
        elif ".js:" in line or ".ts:" in line:
            parts = line.split(":", 1)
            file_path = parts[0]
            
            if os.path.exists(file_path):
                return file_path
            
            rel_path = os.path.join(app_path, file_path)
            if os.path.exists(rel_path):
                return rel_path
    
    main_files = ["app.py", "main.py", "index.js", "server.js"]
    for file in main_files:
        file_path = os.path.join(app_path, file)
        if os.path.exists(file_path):
            return file_path
            
    return None

def fix_file_with_ai(api_client, file_path: str, file_content: str, 
                   error_info: Dict[str, Any], project_context: Dict[str, Any]) -> Optional[str]:
    """Use AI to fix issues in the file based on error messages"""
    fix_context = {
        "file_path": os.path.basename(file_path),
        "file_content": file_content,
        "error_message": error_info.get("stderr", "") + "\n" + error_info.get("stdout", ""),
        "project_context": project_context
    }
    
    response = api_client.call_agent(
        APP_FIXER_PROMPT,
        json.dumps(fix_context),
        max_tokens=4096
    )
    
    if not response:
        return None
        
    return _extract_code_content(response, os.path.basename(file_path))

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
