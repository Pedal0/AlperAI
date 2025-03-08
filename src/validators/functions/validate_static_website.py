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
        
        try:
            webbrowser.open(f"file://{os.path.abspath(index_path)}")
            logger.info(f"Opened static website in browser: {index_path}")
        except Exception as e:
            logger.info(f"Static website could be viewed by opening: {index_path}")
            logger.debug(f"Could not open browser automatically: {str(e)}")
            
        return True
    else:
        index_path = os.path.join(app_path, "src/index.html")
        if os.path.exists(index_path):
            logger.info(f"Static website validated successfully - index.html found at {index_path}")
        
            try:
                webbrowser.open(f"file://{os.path.abspath(index_path)}")
                logger.info(f"Opened static website in browser: {index_path}")
            except Exception as e:
                logger.info(f"Static website could be viewed by opening: {index_path}")
                logger.debug(f"Could not open browser automatically: {str(e)}")
            
            return True
        else:
            logger.error("Static website validation failed - index.html not found")
            return False
