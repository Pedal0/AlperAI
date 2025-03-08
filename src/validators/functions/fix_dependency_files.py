import os
import subprocess
import logging
from typing import Dict, Any

from ..error_fixer import fix_file_with_ai


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _fix_dependency_files(self, app_path: str, language: str, project_context: Dict[str, Any]) -> None:
    """Try to fix dependency files like requirements.txt or package.json"""
    if language == "python":
        req_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(req_path):
            try:
                result = subprocess.run(
                    ["pip", "install", "-r", req_path],
                    cwd=app_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    error_info = {"stdout": result.stdout, "stderr": result.stderr}
                    
                    with open(req_path, 'r') as f:
                        content = f.read()
                    
                    fixed_content = fix_file_with_ai(
                        self.api_client, 
                        req_path,
                        content,
                        error_info,
                        project_context
                    )
                    
                    if fixed_content:
                        with open(req_path, 'w') as f:
                            f.write(fixed_content)
                        logger.info("Fixed requirements.txt file")
            
            except Exception as e:
                logger.error(f"Error fixing requirements.txt: {str(e)}")
    
    elif language in ["javascript", "typescript", "node"]:
        pkg_path = os.path.join(app_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                result = subprocess.run(
                    ["npm", "install"],
                    cwd=app_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    error_info = {"stdout": result.stdout, "stderr": result.stderr}
                    
                    with open(pkg_path, 'r') as f:
                        content = f.read()
                    
                    fixed_content = fix_file_with_ai(
                        self.api_client,
                        pkg_path,
                        content,
                        error_info,
                        project_context
                    )
                    
                    if fixed_content:
                        with open(pkg_path, 'w') as f:
                            f.write(fixed_content)
                        logger.info("Fixed package.json file")
            
            except Exception as e:
                logger.error(f"Error fixing package.json: {str(e)}")
