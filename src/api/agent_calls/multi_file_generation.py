import json
import logging
import re
import os
from typing import Dict, Any, List, Tuple, Optional

from src.config import MULTI_FILE_GENERATOR_PROMPT, MAX_TOKENS_LARGE, MAX_TOKENS_HUGE
from src.file_manager.writer import write_code_to_file

logger = logging.getLogger(__name__)

def generate_multiple_files(api_client, files_spec: List[Dict[str, Any]], project_context: Dict[str, Any], 
                           generation_type: str = "backend") -> Dict[str, str]:
    """
    Generate multiple files in a single API call for better coherence
    
    Args:
        api_client: API client instance
        files_spec: List of file specifications to generate
        project_context: Context information about the project
        generation_type: Type of files to generate (backend, frontend, all)
    
    Returns:
        Dictionary mapping file paths to generated content
    """
    # Prepare context for the API call
    context = {
        "files": files_spec,
        "project_context": project_context,
        "generation_type": generation_type
    }
    
    # Determine max tokens based on number of files to generate
    n_files = len(files_spec)
    if n_files > 10:
        tokens = MAX_TOKENS_HUGE
    elif n_files > 5:
        tokens = MAX_TOKENS_LARGE
    else:
        tokens = MAX_TOKENS_LARGE
    
    logger.info(f"Generating {n_files} {generation_type} files with {tokens} max tokens")
    
    # Make the API call with increased token limit
    response = api_client.call_agent(
        MULTI_FILE_GENERATOR_PROMPT,
        json.dumps(context),
        max_tokens=tokens,
        agent_type="code"
    )
    
    if not response:
        logger.error(f"Failed to generate {generation_type} files")
        return {}
    
    # Special handling for CSS files with JavaScript animations
    if generation_type == "frontend" and '<!-- JAVASCRIPT ANIMATIONS -->' in response:
        # Extract JavaScript animations if present
        js_animations_marker = '<!-- JAVASCRIPT ANIMATIONS -->'
        if js_animations_marker in response:
            css_part, js_part = response.split(js_animations_marker, 1)
            
            # Add JavaScript animations to extracted files
            files_content = extract_files_from_response(css_part)
            
            # Find js/animations.js path and add the JavaScript part
            js_animations_path = "js/animations.js"
            output_dir = project_context.get('output_dir', '')
            
            if output_dir:
                full_js_path = os.path.join(output_dir, js_animations_path)
                os.makedirs(os.path.dirname(full_js_path), exist_ok=True)
                
                # Clean up JavaScript part
                js_content = js_part.strip()
                if js_content.startswith('```javascript'):
                    js_content = js_content.split('\n', 1)[1]
                if js_content.endswith('```'):
                    js_content = js_content.rsplit('\n', 1)[0]
                
                files_content[js_animations_path] = js_content.strip()
            
            return files_content
    
    # Extract all files from the response
    return extract_files_from_response(response)

def extract_files_from_response(response: str) -> Dict[str, str]:
    """
    Extract multiple files from a response with markdown code blocks
    
    The expected format is:
    ```
    ### file/path.ext
    
    File description or comments
    
    ```language
    // filepath: file/path.ext
    file content
    ```
    ```
    
    Returns:
        Dictionary mapping file paths to generated content
    """
    files_content = {}
    
    # Pattern to match file sections with headers and code blocks
    file_sections_pattern = r'#{1,3}\s+(.*?)(?=^#{1,3}\s+|\Z)'
    file_sections = re.findall(file_sections_pattern, response, re.MULTILINE | re.DOTALL)
    
    if not file_sections:
        # Fallback: Try to extract code blocks directly if no section headers found
        code_block_pattern = r'```[\w]*\n// filepath: (.*?)\n([\s\S]*?)```'
        matches = re.findall(code_block_pattern, response)
        
        if not matches:
            # Second fallback: Try to extract just code blocks with language markers
            code_block_pattern = r'```([\w]+)\n([\s\S]*?)```'
            language_blocks = re.findall(code_block_pattern, response)
            
            # Map language to likely file extensions
            language_to_ext = {
                'python': '.py',
                'javascript': '.js',
                'typescript': '.ts', 
                'html': '.html',
                'css': '.css',
                'json': '.json',
                'php': '.php'
            }
            
            # Create filenames based on content
            for i, (lang, content) in enumerate(language_blocks):
                ext = language_to_ext.get(lang.lower(), f'.{lang}')
                filename = f"generated_file_{i+1}{ext}"
                files_content[filename] = content.strip()
            
            return files_content
            
        for file_path, content in matches:
            file_path = file_path.strip()
            files_content[file_path] = content.strip()
        
        return files_content
    
    # Process each file section
    for section in file_sections:
        # Extract file path from section header
        file_path_match = re.match(r'^(.+?)(?:\n|$)', section.strip())
        if not file_path_match:
            continue
            
        file_path = file_path_match.group(1).strip()
        
        # Extract code block from the section
        code_block_pattern = r'```[\w]*\n(?:// filepath: .*?\n)?([\s\S]*?)```'
        code_match = re.search(code_block_pattern, section)
        
        if code_match:
            content = code_match.group(1).strip()
            files_content[file_path] = content
        else:
            # Fallback: Use all text after the header if no code block found
            content = section[file_path_match.end():].strip()
            if content:
                files_content[file_path] = content
    
    return files_content

def write_multiple_files(output_path: str, files_content: Dict[str, str]) -> List[str]:
    """
    Write multiple generated files to disk
    
    Args:
        output_path: Base output directory
        files_content: Dictionary mapping file paths to content
    
    Returns:
        List of absolute paths to written files
    """
    written_files = []
    for file_path, content in files_content.items():
        try:
            absolute_path = write_code_to_file(output_path, file_path, content)
            written_files.append(absolute_path)
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {str(e)}")
    
    return written_files
