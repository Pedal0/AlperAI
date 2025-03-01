import json
import os
import time
import random
import re
from openai import OpenAI
from src.config import (
    OPENROUTER_API_KEY, 
    STRUCTURE_MODEL, 
    CODE_MODEL,
    CORRECT_CODE_MODEL,
    STRUCTURE_SYSTEM_PROMPT,
    CODE_SYSTEM_PROMPT,
    CORRECT_CODE_SYSTEM_PROMPT,
    MAX_RETRIES
)
from src.json_utils import extract_json, normalize_structure
from src.file_utils import get_flat_file_list, save_corrected_files
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
    la clé est le nom du fichier et la valeur est une description de son contenu.
    
    IMPORTANT: Pour chaque fichier, inclus TOUJOURS dans la description une liste détaillée des variables, 
    fonctions, classes et composants à implémenter avec leurs noms exacts. Sois très précis sur les noms 
    des variables à utiliser pour faciliter l'intégration entre les fichiers.
    
    Par exemple pour une application Flask:
    {{
      "app.py": "Point d'entrée de l'application Flask. Variables: app (Flask instance), db (database connection), Variables globales: UPLOAD_FOLDER, ALLOWED_EXTENSIONS. Fonctions: create_app(), init_db(), allowed_file(filename)",
      "requirements.txt": "Dépendances du projet: flask, flask-sqlalchemy, etc.",
      "static": {{
        "css": {{
          "style.css": "Styles principaux. Classes CSS: header, navigation, footer, card, button-primary"
        }},
        "js": {{
          "main.js": "Scripts JavaScript. Fonctions: initApp(), handleFormSubmit(formData), toggleMenu(). Variables: apiEndpoint, userData"
        }}
      }},
      "templates": {{
        "base.html": "Template de base. Blocks Jinja: title, content, scripts",
        "index.html": "Page d'accueil. Variables passées du backend: user_name, items_list"
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
    
    Focntions qui ont déjà été implémentées:
    {functions_info}
    
    Fichier à générer: {file_path}
    Description: {file_description}
    
    Génère le code complet de ce fichier. Assure-toi qu'il respecte les bonnes pratiques
    de son langage et qu'il s'intègre correctement avec les autres fichiers du projet.
    NE MODIFIE PAS les fonctions existantes, utilise-les telles quelles en prenant en compte les fonctions deja implémentées.
    Réponds uniquement avec le code, sans explication ni commentaire autour du code.
    Prend une attention particuliere aux détails et à la qualité du code.
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

def _clean_ai_comments(code):
    """
    Nettoie le code des commentaires explicatifs potentiellement ajoutés par l'IA.
    
    Args:
        code (str): Le code à nettoyer
        
    Returns:
        str: Le code nettoyé
    """
    # Supprimer les commentaires qui pourraient contenir "PARFAIT" ou des explications
    lines = code.split('\n')
    cleaned_lines = []
    
    skip_block = False
    for line in lines:
        line_lower = line.strip().lower()
        
        # Ignorer les lignes de commentaires explicatifs de l'IA
        if any(pattern in line_lower for pattern in [
            "# ce fichier est parfait",
            "# file is perfect",
            "# le code est parfait",
            "# code is perfect",
            "# no changes needed", 
            "# aucune modification nécessaire",
            "# explanation:",
            "# explication:",
            "# note:"
        ]):
            continue
            
        # Suppression des blocs de commentaires explicatifs
        if line_lower.startswith('"""') or line_lower.startswith("'''"):
            if not skip_block:
                skip_block = True
                continue
            else:
                skip_block = False
                continue
                
        if not skip_block:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def verify_project_files(project_description, project_structure, files_content):
    """
    Vérifie l'intégrité du code généré pour les fichiers du projet.
    
    Args:
        project_description (str): Description du projet
        project_structure (dict): Structure du projet
        files_content (dict): Contenu des fichiers générés
        
    Returns:
        dict: Dictionnaire de résultats avec les clés:
            - 'needs_correction': True/False
            - 'modified_files': dict des fichiers modifiés (chemin => contenu)
            - 'suggestions': dict des suggestions textuelles (chemin => suggestion)
            - 'analysis_results': dict des résultats d'analyse (chemin => "PARFAIT" ou "MODIFIÉ")
    """
    project_functions = collect_project_functions(files_content)
    function_info = format_function_info(project_functions)
    
    results = {
        'needs_correction': False,
        'modified_files': {},
        'suggestions': {},
        'analysis_results': {}
    }
    
    # Créer un contexte global avec tous les fichiers pour une meilleure référence
    all_files_context = ""
    for fp, cnt in files_content.items():
        all_files_context += f"\n--- Fichier: {fp} ---\n"
        # Limiter à quelques lignes pour éviter des prompts trop longs
        lines = cnt.split('\n')
        if len(lines) > 50:
            preview = '\n'.join(lines[:25]) + "\n...\n" + '\n.join(lines[-25:])'
            all_files_context += preview + "\n"
        else:
            all_files_context += cnt + "\n"
    
    for file_path, content in files_content.items():
        # Ignorer les fichiers non-code
        if file_path.endswith(('.jpg', '.png', '.gif', '.svg', '.ico', '.ttf', '.woff')):
            continue
        
        file_ext = os.path.splitext(file_path)[1].lower()
        prompt = f"""
        Vérifie l'intégrité de ce fichier et corrige-le si nécessaire.
        
        Description du projet:
        {project_description}
        
        Structure complète du projet:
        {json.dumps(project_structure, indent=2)}
        
        Fonctions dans le projet:
        {function_info}
        
        CONTEXTE IMPORTANT - Autres fichiers du projet (résumé):
        {all_files_context}
        
        FICHIER À VÉRIFIER:
        {file_path}
        
        ```
        {content}
        ```
        
        INSTRUCTIONS:
        1. Vérifie les problèmes suivants:
           - Importations manquantes ou incorrectes
           - Appels à des fonctions avec des noms ou paramètres incorrects
           - Variables non définies ou mal référencées
           - Incompatibilités avec le reste du projet
           - Erreurs de syntaxe ou logique
        
        2. Si le code est parfait, réponds UNIQUEMENT avec le mot "PARFAIT" sans autre texte, explication ou commentaire.
        
        3. Si des corrections sont nécessaires:
           - Fournis UNIQUEMENT le code corrigé COMPLET du fichier
           - Ne donne pas d'explications ni de commentaires explicatifs
           - N'ajoute pas de commentaires pour justifier tes changements
        """
        
        try:
            _ensure_rate_limit()
            completion = client.chat.completions.create(
                model=CORRECT_CODE_MODEL,
                messages=[
                    {"role": "system", "content": CORRECT_CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            response = completion.choices[0].message.content
            
            # Nettoyage de la réponse
            response = response.strip()
            
            # Vérifier si la réponse est "PARFAIT" (potentiellement avec des espaces ou sauts de ligne)
            is_perfect = False
            if re.match(r'^PARFAIT\s*$', response, re.IGNORECASE):
                is_perfect = True
            
            if is_perfect:
                results['suggestions'][file_path] = "Le code est parfait, aucune correction nécessaire."
                results['analysis_results'][file_path] = "PARFAIT"
                continue
            
            # Extraction du code corrigé
            code_corrected = response
            
            # Si le code est dans un bloc de code markdown, on l'extrait
            if code_corrected.startswith("```") and "```" in code_corrected[3:]:
                match = re.search(r'```(?:\w+)?\s*([\s\S]+?)\s*```', code_corrected)
                if match:
                    code_corrected = match.group(1)
            
            # Nettoyer les commentaires explicatifs ajoutés par l'IA
            code_corrected = _clean_ai_comments(code_corrected)
            
            # S'assurer que le code est significativement différent
            # (éviter les modifications mineures comme des espaces ou commentaires)
            if code_corrected.strip() != content.strip():
                # Vérifier si les changements sont substantiels (pas juste des espaces ou commentaires)
                content_no_comments = re.sub(r'#.*$', '', content, flags=re.MULTILINE).strip()
                corrected_no_comments = re.sub(r'#.*$', '', code_corrected, flags=re.MULTILINE).strip()
                
                if content_no_comments != corrected_no_comments:
                    results['needs_correction'] = True
                    results['modified_files'][file_path] = code_corrected
                    results['suggestions'][file_path] = f"Le fichier a été corrigé pour résoudre des problèmes d'intégration."
                    results['analysis_results'][file_path] = "MODIFIÉ"
                else:
                    # Si seuls les commentaires ont changé, considérer comme parfait
                    results['suggestions'][file_path] = "Le code est fonctionnel, seuls des commentaires ont été modifiés."
                    results['analysis_results'][file_path] = "PARFAIT"
        
        except Exception as e:
            print(f"⚠️ Erreur lors de la vérification du fichier {file_path}: {str(e)}")
            results['suggestions'][file_path] = f"Erreur lors de la vérification: {str(e)}"
            results['analysis_results'][file_path] = "ERREUR"
    
    return results