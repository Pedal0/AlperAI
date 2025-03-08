import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def write_code_to_file(output_path: str, file_path: str, code_content: str) -> str:
    """Write code content to a file and return the absolute path"""
    absolute_path = os.path.join(output_path, file_path)
    
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    
    cleaned_content = _clean_markdown_code_blocks(code_content)
    
    try:
        with open(absolute_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        logger.info(f"Successfully wrote file: {absolute_path}")
        return absolute_path
    except Exception as e:
        logger.error(f"Failed to write file {absolute_path}: {str(e)}")
        return ""

def _clean_markdown_code_blocks(content: str) -> str:
    """Remove markdown code block formatting from generated content"""
    pattern = r"```[a-zA-Z0-9_+#-]*\n([\s\S]*?)\n```"
    
    matches = re.findall(pattern, content)
    if matches:
        return matches[0]
    
    return content
