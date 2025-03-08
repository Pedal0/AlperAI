import os
import logging
from typing import Set

logger = logging.getLogger(__name__)

def create_directories(directories: Set[str]) -> None:
    """Create all necessary directories for the project"""
    for directory in sorted(directories):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
