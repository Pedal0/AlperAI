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

def extract_function_signatures(content: str, language: str) -> List[Dict]:
    """
    Extrait les signatures des fonctions à partir du contenu d'un fichier.
    
    Args:
        content (str): Contenu du fichier
        language (str): Langage du fichier
        
    Returns:
        List[Dict]: Liste des signatures de fonctions
    """
    if language == 'python':
        return extract_python_functions(content)
    elif language in ['javascript', 'typescript']:
        return extract_js_functions(content)
    elif language == 'php':
        return extract_php_functions(content)
    elif language == 'java':
        return extract_java_functions(content)
    elif language == 'csharp':
        return extract_csharp_functions(content)
    elif language == 'ruby':
        return extract_ruby_functions(content)
    elif language == 'go':
        return extract_go_functions(content)
    else:
        return []

def extract_python_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des fonctions Python.
    """
    functions = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = []
                for arg in node.args.args:
                    params.append(arg.arg)
                
                functions.append({
                    "name": node.name,
                    "params": params,
                    "docstring": ast.get_docstring(node)
                })
    except SyntaxError:
        function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)'
        for match in re.finditer(function_pattern, content):
            name = match.group(1)
            params_str = match.group(2).strip()
            params = [p.strip().split(':')[0].split('=')[0].strip() for p in params_str.split(',') if p.strip()]
            functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_js_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des fonctions JavaScript/TypeScript.
    """
    functions = []
    
    pattern1 = r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)'
    pattern2 = r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*(?:async\s+)?(?:function\s*)?\(([^)]*)\)'
    pattern3 = r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)\s*{'
    
    for pattern in [pattern1, pattern2, pattern3]:
        for match in re.finditer(pattern, content):
            name = match.group(1)
            params_str = match.group(2).strip()
            params = [p.strip().split('=')[0].strip() for p in params_str.split(',') if p.strip()]
            functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_php_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des fonctions PHP.
    """
    functions = []
    pattern = r'function\s+([a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*)\s*\(([^)]*)\)'
    
    for match in re.finditer(pattern, content):
        name = match.group(1)
        params_str = match.group(2).strip()
        params = [p.strip().split('=')[0].strip().lstrip('$') for p in params_str.split(',') if p.strip()]
        functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_java_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des méthodes Java.
    """
    functions = []
    pattern = r'(?:public|protected|private|static|\s) +(?:[a-zA-Z0-9_<>[\],\s]+) +([a-zA-Z0-9_]+) *\(([^)]*)\)'
    
    for match in re.finditer(pattern, content):
        name = match.group(1)
        params_str = match.group(2).strip()
        params = []
        if params_str:
            for param in params_str.split(','):
                parts = param.strip().split()
                if len(parts) >= 2:
                    params.append(parts[-1])
        
        functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_csharp_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des méthodes C#.
    """
    functions = []
    pattern = r'(?:public|protected|private|internal|static|\s) +(?:[a-zA-Z0-9_<>[\],\s\.]+) +([a-zA-Z0-9_]+) *\(([^)]*)\)'
    
    for match in re.finditer(pattern, content):
        name = match.group(1)
        params_str = match.group(2).strip()
        params = []
        if params_str:
            for param in params_str.split(','):
                parts = param.strip().split()
                if len(parts) >= 2:
                    params.append(parts[-1])
        
        functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_ruby_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des méthodes Ruby.
    """
    functions = []
    pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*[?!]?)\s*(?:\(([^)]*)\))?'
    
    for match in re.finditer(pattern, content):
        name = match.group(1)
        params_str = match.group(2) if match.group(2) else ""
        params = [p.strip().split('=')[0].strip() for p in params_str.split(',') if p.strip()]
        functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

def extract_go_functions(content: str) -> List[Dict]:
    """
    Extrait les signatures des fonctions Go.
    """
    functions = []
    pattern = r'func\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)'
    
    for match in re.finditer(pattern, content):
        name = match.group(1)
        params_str = match.group(2).strip()
        params = []
        if params_str:
            param_groups = re.findall(r'(?:[^\s,]+\s+)+[^\s,]+', params_str)
            for group in param_groups:
                param_names = group.split()[:-1]
                params.extend(param_names)
        
        functions.append({"name": name, "params": params, "docstring": None})
    
    return functions

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
