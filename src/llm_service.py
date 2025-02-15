import json
import re
from openai import OpenAI
from src.config import OPENROUTER_API_KEY
from src.json_utils import extract_json, normalize_structure

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_project_structure(prompt):
    """Envoie le prompt à l'IA et récupère la structure du projet au format JSON."""
    for attempt in range(3): 
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct:free",
            messages=[
                {"role": "system", "content": "Tu es un assistant spécialisé dans la génération de structures de projet. Réponds uniquement avec un JSON valide décrivant les fichiers et dossiers. Tous les dossiers doivent être des dictionnaires et tous les fichiers doivent être des chaînes vides (\"\"), par exemple: {\"dossier\": {\"SousDossier\": {\"fichier.py\": \"\", \"autre_fichier.txt\": \"\"}}}. Ne renvoie que le JSON, sans explication ni texte supplémentaire."},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = extract_json(completion.choices[0].message.content)
        try:
            structure = json.loads(response_text)
            return normalize_structure(structure) 
        except json.JSONDecodeError:
            print(f"⚠️ Erreur de format JSON. Tentative {attempt + 1} sur 3...")
            prompt = f"Corrige ce JSON invalide : {response_text}"
            print(prompt)
    
    print("❌ Le LLM n'a pas réussi à fournir un JSON valide après plusieurs tentatives.")
    return None
