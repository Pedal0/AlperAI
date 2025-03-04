import ast
import re
from typing import Dict, List, Optional

def detect_language(file_path: str) -> str:
    """
    Détecte le langage de programmation en fonction de l'extension du fichier.
    
    Args:
        file_path (str): Chemin du fichier
        
    Returns:
        str: Nom du langage détecté
    """
    extension = file_path.split('.')[-1].lower() if '.' in file_path else ""
    
    language_map = {
        'py': 'python',
        'js': 'javascript',
        'jsx': 'javascript',
        'ts': 'typescript',
        'tsx': 'typescript',
        'php': 'php',
        'java': 'java',
        'cs': 'csharp',
        'rb': 'ruby',
        'go': 'go',
        'html': 'html',
        'css': 'css'
    }
    
    return language_map.get(extension, 'unknown')