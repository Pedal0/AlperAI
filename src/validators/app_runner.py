import os
import subprocess
import logging
import time
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

def try_start_application(app_path: str, start_cmd: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Try to start the application and verify it runs correctly"""
    logger.info(f"Starting application with: {' '.join(start_cmd)}")
    
    try:
        if start_cmd[0] in ["cmd", "echo"]:
            logger.warning("Using fallback command, skipping execution test")
            return False, {"error": "No suitable entry point found", "cmd": start_cmd}
            
        process = subprocess.Popen(
            start_cmd,
            cwd=app_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(20)
        
        if process.poll() is None:
            process.terminate()
            return True, {}
        else:
            stdout, stderr = process.communicate()
            
            error_info = {
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "cmd": start_cmd
            }
            
            logger.error(f"Application failed to start. Error: {stderr}")
            return False, error_info
            
    except Exception as e:
        logger.error(f"Exception during application start: {str(e)}")
        return False, {"error": str(e), "cmd": start_cmd}
