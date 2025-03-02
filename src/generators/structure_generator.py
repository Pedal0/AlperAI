import json
import time
from openai import OpenAI
from src.config import (
    OPENAI_API_KEY,
    # OPENROUTER_API_KEY,
    STRUCTURE_MODEL,
    STRUCTURE_SYSTEM_PROMPT,
    MAX_RETRIES
)
from src.json_utils import extract_json, normalize_structure

client = OpenAI(
    api_key=OPENAI_API_KEY,
    # base_url="https://openrouter.ai/api/v1",
    # api_key=OPENROUTER_API_KEY,
)

_last_api_call_time = 0
delay_between_calls = 1
def _ensure_rate_limit():
    """
    Ensures there's a delay of 10-11 seconds between API calls.
    """
    global _last_api_call_time
    current_time = time.time()
    elapsed = current_time - _last_api_call_time
    
    if _last_api_call_time > 0 and elapsed < delay_between_calls:
        delay = delay_between_calls - elapsed
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
