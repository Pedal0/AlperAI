import json
import os
import time
import random
from openai import OpenAI
from src.config import (
    OPENROUTER_API_KEY, 
    STRUCTURE_MODEL, 
    CODE_MODEL,
    STRUCTURE_SYSTEM_PROMPT,
    CODE_SYSTEM_PROMPT,
    MAX_RETRIES
)
from src.json_utils import extract_json, normalize_structure
from src.file_utils import get_flat_file_list
from src.code_analyzer import collect_project_functions, format_function_info

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

_file_cache = {}
_last_api_call_time = 0

def _ensure_rate_limit():
    """
    Ensures there's a delay of 10-11 seconds between API calls.
    """
    global _last_api_call_time
    current_time = time.time()
    elapsed = current_time - _last_api_call_time
    
    if _last_api_call_time > 0 and elapsed < 11:
        delay = 11 - elapsed
        print(f"⏱️ Attente de {delay:.1f} secondes pour respecter la limite d'API...")
        time.sleep(delay)
    
    _last_api_call_time = time.time()

def generate_project_structure(project_description):
    """
    Génère la structure du projet à partir de la description utilisateur.
    
    Args:
        project_description (str): Description du projet
        
    Returns:
        dict: Structure du projet sous forme de dictionnaire imbriqué
    """
    prompt = f"""
    Crée une structure de projet pour le site web ou l'application suivant:
    
    {project_description}
    
    Réponds seulement avec un objet JSON représentant la structure de fichiers et dossiers.
    Les dossiers sont des objets imbriqués et les fichiers sont des paires clé-valeur où
    la clé est le nom du fichier et la valeur est une brève description de son contenu.
    
    Par exemple pour une application Flask:
    {{
      "app.py": "Point d'entrée de l'application Flask",
      "requirements.txt": "Dépendances du projet",
      "static": {{
        "css": {{
          "style.css": "Styles principaux"
        }},
        "js": {{
          "main.js": "Scripts JavaScript"
        }}
      }},
      "templates": {{
        "base.html": "Template de base",
        "index.html": "Page d'accueil"
      }}
    }}
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            _ensure_rate_limit()
            completion = client.chat.completions.create(
                model=STRUCTURE_MODEL,
                messages=[
                    {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = completion.choices[0].message.content
            json_text = extract_json(response_text)
            
            if json_text:
                structure = json.loads(json_text)
                normalized_structure = normalize_structure(structure)
                return normalized_structure
            else:
                print(f"⚠️ Tentative {attempt+1}: Impossible d'extraire un JSON valide.")
                
        except Exception as e:
            print(f"⚠️ Erreur lors de la tentative {attempt+1}: {str(e)}")
    
    raise Exception("Échec de la génération de la structure après plusieurs tentatives")

def generate_file_content(project_description, file_path, file_description, project_structure, files_content=None):
    """
    Génère le contenu d'un fichier spécifique.
    
    Args:
        project_description (str): Description du projet
        file_path (str): Chemin du fichier
        file_description (str): Description du fichier
        project_structure (dict): Structure complète du projet
        files_content (dict, optional): Contenu des fichiers déjà générés
        
    Returns:
        str: Contenu du fichier
    """
    if file_path in _file_cache:
        return _file_cache[file_path]
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Information des fonctions existantes à ajouter au prompt
    functions_info = ""
    if files_content:
        project_functions = collect_project_functions(files_content)
        if project_functions:
            functions_info = format_function_info(project_functions)
    
    prompt = f"""
    Description du projet:
    {project_description}
    
    Structure complète du projet:
    {json.dumps(project_structure, indent=2)}
    
    {functions_info}
    
    Fichier à générer: {file_path}
    Description: {file_description}
    
    Génère le code complet de ce fichier. Assure-toi qu'il respecte les bonnes pratiques
    de son langage et qu'il s'intègre correctement avec les autres fichiers du projet.
    NE MODIFIE PAS les fonctions existantes, utilise-les telles quelles.
    Réponds uniquement avec le code, sans explication ni commentaire autour du code.
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            _ensure_rate_limit()
            completion = client.chat.completions.create(
                model=CODE_MODEL,
                messages=[
                    {"role": "system", "content": CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            file_content = completion.choices[0].message.content
            
            file_content = file_content.strip()
            if file_content.startswith("```") and file_content.endswith("```"):
                lang_hint = file_content.split("\n")[0].replace("```", "").strip()
                if lang_hint:
                    file_content = "\n".join(file_content.split("\n")[1:])
                file_content = file_content.rstrip("```").strip()
            
            _file_cache[file_path] = file_content
            return file_content
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la génération du fichier {file_path} (tentative {attempt+1}): {str(e)}")
    
    error_content = f"# Erreur: Impossible de générer le contenu pour {file_path}\n"
    _file_cache[file_path] = error_content
    return error_content

def generate_project_files(project_description, project_structure, regenerate=True):
    """
    Génère tous les fichiers du projet.
    
    Args:
        project_description (str): Description du projet
        project_structure (dict): Structure du projet
        regenerate (bool): Si True, régénère les fichiers même s'ils sont en cache
        
    Returns:
        dict: Dictionnaire avec les chemins et contenus des fichiers
    """
    if regenerate:
        _file_cache.clear()
    
    flat_files = get_flat_file_list(project_structure)
    
    files_content = {}
    for file_path, description in flat_files:
        content = generate_file_content(
            project_description, 
            file_path, 
            description, 
            project_structure,
            files_content
        )
        files_content[file_path] = content
    
    return files_content