from typing import Dict, List
from src.analyzers.language_detector import detect_language
from src.analyzers.function_extractor import extract_function_signatures

def collect_project_functions(files_content: Dict[str, str]) -> Dict[str, List[Dict]]:
    """
    Collecte toutes les signatures de fonctions pour chaque fichier du projet.
    
    Args:
        files_content (Dict[str, str]): Dictionnaire avec les chemins et contenus des fichiers
        
    Returns:
        Dict[str, List[Dict]]: Dictionnaire des signatures de fonctions par fichier
    """
    project_functions = {}
    
    for file_path, content in files_content.items():
        language = detect_language(file_path)
        if language != 'unknown':
            functions = extract_function_signatures(content, language)
            if functions:
                project_functions[file_path] = functions
    
    return project_functions

def format_function_info(project_functions: Dict[str, List[Dict]]) -> str:
    """
    Formate les informations des fonctions pour une utilisation dans le prompt.
    
    Args:
        project_functions (Dict[str, List[Dict]]): Dictionnaire des signatures de fonctions par fichier
        
    Returns:
        str: Texte formaté des informations de fonctions
    """
    result = "Fonctions existantes dans le projet:\n\n"
    
    for file_path, functions in project_functions.items():
        if functions:
            language = detect_language(file_path)
            result += f"Fichier: {file_path} (langage: {language})\n"
            for func in functions:
                params_str = ", ".join(func["params"])
                result += f"  - {func['name']}({params_str})\n"
            result += "\n"
    
    return result
