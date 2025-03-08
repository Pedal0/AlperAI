import os
import re
import logging
from typing import Dict, Any, List
from .writer import write_code_to_file
from .structure_creator import create_directories

logger = logging.getLogger(__name__)

class FileSystemManager:
    def __init__(self):
        pass
        
    def create_project_structure(self, output_path: str, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create project structure based on the architecture specification"""
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
        
        create_directories(directories)
            
        for directory in directories:
            if any(os.path.basename(f) == "__init__.py" for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))):
                continue
            
            if any(f.endswith(".py") for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))):
                init_path = os.path.join(directory, "__init__.py")
                with open(init_path, 'w') as f:
                    f.write("")
                    
        return files_to_generate
    
    def write_code_to_file(self, output_path: str, file_path: str, code_content: str) -> str:
        """Write code to a file and return the absolute path"""
        return write_code_to_file(output_path, file_path, code_content)

    def _clean_markdown_code_blocks(self, content: str) -> str:        
        pattern = r"```[a-zA-Z0-9_+#-]*\n([\s\S]*?)\n```"
        
        matches = re.findall(pattern, content)
        if matches:
            return matches[0]
        
        return content