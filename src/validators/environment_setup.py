import os
import sys
import subprocess
import logging
from typing import List

logger = logging.getLogger(__name__)

def setup_environment(app_path: str, setup_cmds: List[str]) -> bool:
    """Set up the environment for the application with required dependencies"""
    try:
        for cmd in setup_cmds:
            logger.info(f"Running: {cmd}")
            shell = True if sys.platform == "win32" else False
            process = subprocess.run(
                cmd, 
                shell=shell, 
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=180 
            )
            
            if process.returncode != 0:
                logger.error(f"Command failed: {cmd}")
                logger.error(f"Error: {process.stderr}")
                return False
                
        return True
    except Exception as e:
        logger.error(f"Environment setup failed: {str(e)}")
        return False
