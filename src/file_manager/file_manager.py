import os
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FileSystemManager:
    def __init__(self):
        pass
        
    def create_project_structure(self, output_path: str, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        files_to_generate = []
        directories = set()
        
        for file_spec in architecture.get("files", []):
            file_path = file_spec.get("path", "")
            if file_path:
                dir_path = os.path.dirname(file_path)
                if dir_path:
                    directories.add(os.path.join(output_path, dir_path))
                files_to_generate.append(file_spec)
        
        for directory in sorted(directories):
            os.makedirs(directory, exist_ok=True)
            
        for directory in directories:
            if any(os.path.basename(f) == "__init__.py" for f in os.listdir(directory)):
                continue
            
            if any(f.endswith(".py") for f in os.listdir(directory)):
                init_path = os.path.join(directory, "__init__.py")
                with open(init_path, 'w') as f:
                    f.write("")
                    
        return files_to_generate
    
    def write_code_to_file(self, output_path: str, file_path: str, code_content: str) -> str:
        absolute_path = os.path.join(output_path, file_path)
        
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        
        # Clean markdown code blocks formatting
        cleaned_content = self._clean_markdown_code_blocks(code_content)
        
        with open(absolute_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
            
        return absolute_path

    def _clean_markdown_code_blocks(self, content: str) -> str:        
        pattern = r"```[a-zA-Z0-9_+#-]*\n([\s\S]*?)\n```"
        
        matches = re.findall(pattern, content)
        if matches:
            return matches[0]
        
        return content
    
    def create_requirements_file(self, output_path: str, dependencies: List[str]) -> str:
        requirements_path = os.path.join(output_path, "requirements.txt")
        
        with open(requirements_path, 'w', encoding='utf-8') as f:
            for dependency in dependencies:
                f.write(f"{dependency}\n")
                
        return requirements_path
    
    def create_readme(self, output_path: str, project_info: Dict[str, Any]) -> str:
        readme_path = os.path.join(output_path, "README.md")
        
        tech_stack = project_info.get('technical_stack', {})
        language = tech_stack.get('language', 'python').lower() if isinstance(tech_stack, dict) else 'python'
        
        # Fix the components type check
        components = project_info.get('components', [])
        
        # Add safeguard against non-list components
        if not isinstance(components, list):
            logger.warning(f"Components is not a list: {type(components)}")
            components = []
            
        # Check for frontend and backend components with proper type checking
        has_frontend = any(
            isinstance(comp, dict) and comp.get('type', '') == 'frontend' 
            for comp in components
        )
        
        has_backend = any(
            isinstance(comp, dict) and comp.get('type', '') == 'backend' 
            for comp in components
        )
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"# {project_info.get('app_name', 'Generated Application')}\n\n")
            f.write(f"{project_info.get('app_description', '')}\n\n")
            
            f.write("## Installation\n\n")
            
            if language in ['javascript', 'typescript', 'node', 'react', 'vue', 'angular']:
                f.write("```bash\nnpm install\n```\n\n")
            else:
                f.write("```bash\npip install -r requirements.txt\n```\n\n")
            
            f.write("## Usage\n\n")
            
            if has_frontend and has_backend:
                f.write("### Backend\n\n")
                if language == 'python':
                    f.write(f"```bash\npython backend/{project_info.get('main_file', 'app.py')}\n```\n\n")
                else:
                    f.write("```bash\ncd backend\nnpm start\n```\n\n")
                    
                f.write("### Frontend\n\n")
                f.write("```bash\ncd frontend\nnpm start\n```\n\n")
            else:
                if language in ['javascript', 'typescript', 'node', 'react', 'vue', 'angular']:
                    f.write("```bash\nnpm start\n```\n\n")
                else:
                    f.write(f"```bash\npython {project_info.get('main_file', 'app.py')}\n```\n\n")
            
            f.write("## Features\n\n")
            requirements = project_info.get("requirements", [])
            if isinstance(requirements, list):
                for req in requirements:
                    if isinstance(req, str):
                        f.write(f"- {req}\n")
                    elif isinstance(req, dict) and "description" in req:
                        f.write(f"- {req['description']}\n")
                
        return readme_path