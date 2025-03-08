import logging
from typing import Dict, Any

from ..app_runner import try_start_application
from ..error_fixer import identify_error_file, fix_file_with_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _attempt_fix_application(self, app_path: str, error_info: Dict[str, Any], 
                           project_context: Dict[str, Any]) -> bool:
    """Attempt to fix application issues automatically"""
    for attempt in range(self.max_fix_attempts):
        logger.info(f"Fix attempt {attempt + 1}/{self.max_fix_attempts}")
        
        error_file = identify_error_file(app_path, error_info)
        if not error_file:
            logger.error("Could not identify the file causing the error")
            return False
            
        try:
            with open(error_file, 'r') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Could not read file {error_file}: {str(e)}")
            return False
            
        fixed_content = fix_file_with_ai(
            self.api_client,
            error_file, 
            file_content, 
            error_info, 
            project_context
        )
        
        if not fixed_content:
            logger.error("Failed to get fixed content from AI")
            return False
            
        try:
            with open(error_file, 'w') as f:
                f.write(fixed_content)
        except Exception as e:
            logger.error(f"Could not write fixed content to {error_file}: {str(e)}")
            return False
            
        env_setup_cmds, start_cmd = self._get_env_and_start_commands(
            app_path, 
            project_context.get("architecture", {}).get("language", "python").lower()
        )
        
        success, new_error_info = try_start_application(app_path, start_cmd)
        
        if success:
            logger.info("Application fixed and started successfully")
            return True
            
        error_info = new_error_info
        
    logger.error(f"Failed to fix application after {self.max_fix_attempts} attempts")
    return False
