import os
import logging
import webbrowser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _validate_static_website(self, app_path: str) -> bool:
    """Validate a static website by checking for index.html"""
    index_path = os.path.join(app_path, "index.html")
    
    if os.path.exists(index_path):
        logger.info(f"Static website validated successfully - index.html found at {index_path}")
        
        # N'ouvre plus le navigateur automatiquement
        logger.info(f"Static website can be viewed by opening: {index_path}")
        return True
    else:
        index_path = os.path.join(app_path, "src/index.html")
        if os.path.exists(index_path):
            logger.info(f"Static website validated successfully - index.html found at {index_path}")
            logger.info(f"Static website can be viewed by opening: {index_path}")
            return True
        else:
            logger.error("Static website validation failed - index.html not found")
            return False
