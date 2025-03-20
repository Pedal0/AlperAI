import json
import logging
import os
from typing import Dict, Any, List, Optional

from src.config import CODE_GENERATOR_PROMPT, CSS_DESIGNER_PROMPT, PROJECT_FILES_GENERATOR_PROMPT, MAX_TOKENS_LARGE, MAX_TOKENS_DEFAULT

logger = logging.getLogger(__name__)

def generate_code(api_client, file_spec: Dict[str, Any], project_context: Dict[str, Any]) -> str:
    """Generate code for a specified file"""
    file_path = file_spec.get("path", "")
    file_type = file_spec.get("type", "")
    file_purpose = file_spec.get("purpose", "")
    
    # Détecter les fichiers CSS pour un traitement spécial
    is_css_file = file_path.endswith('.css')
    
    prompt = CSS_DESIGNER_PROMPT if is_css_file else CODE_GENERATOR_PROMPT
    
    context = {
        "file": file_spec,
        "project_context": project_context
    }
    
    # Ajouter l'information sur le HTML associé pour CSS
    if is_css_file:
        html_files = {}
        for file_path, content in project_context.get('existing_files', {}).items():
            if file_path.endswith(('.html', '.htm')):
                html_files[file_path] = content
        
        context["html_files"] = html_files
        context["js_animation_path"] = "js/animations.js"
    
    response = api_client.call_agent(
        prompt, 
        json.dumps(context), 
        max_tokens=MAX_TOKENS_LARGE,
        agent_type="css" if is_css_file else "code"
    )
    
    # Pour CSS, traiter séparément le CSS et JavaScript
    if is_css_file and '<!-- JAVASCRIPT ANIMATIONS -->' in response:
        css_part, js_part = response.split('<!-- JAVASCRIPT ANIMATIONS -->', 1)
        
        # Écrire le JavaScript dans un fichier séparé
        js_path = os.path.join(os.path.dirname(os.path.dirname(file_path)), "js/animations.js")
        output_dir = project_context.get('output_dir', '')
        
        if output_dir:
            full_js_path = os.path.join(output_dir, js_path)
            os.makedirs(os.path.dirname(full_js_path), exist_ok=True)
            
            with open(full_js_path, 'w', encoding='utf-8') as f:
                f.write(js_part.strip())
            
            logger.info(f"JavaScript animations written to {js_path}")
        
        return css_part.strip()
    
    return response

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
