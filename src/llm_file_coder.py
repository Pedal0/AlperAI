import json
import re
from openai import OpenAI
from src.config import OPENROUTER_API_KEY
from src.json_utils import extract_json, normalize_structure

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_file_comments(user_prompt, file_name, project_structure):
    """
    Génère pour un fichier une liste de commentaires concis préfixés par '#' 
    indiquant brièvement ce qu'il faudra mettre dans le fichier. 
    Pour cela, il transmet :
      - le prompt utilisateur décrivant le projet,
      - le nom du fichier actuel,
      - et la structure complète du projet en JSON.
    """
    composed_prompt = (
        f"Question : {user_prompt}\n\n"
        f"Structure du projet (JSON) :\n{json.dumps(project_structure, indent=2)}\n\n"
        f"Fichier actuel : {file_name}\n\n"
        "Génère une petite liste de commentaires concis. Chaque ligne doit débuter par '#' "
        "pour indiquer brièvement ce qu'il faut inclure dans ce fichier. Réponds uniquement avec des commentaires, sans code."
    )

    for attempt in range(3):
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct:free",
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un assistant spécialisé dans la génération d'instructions sous forme de commentaires pour la création d'applications. Répondez uniquement avec une liste de commentaires concis, chaque ligne débutant par '#' pour décrire ce qu'il faut inclure dans le fichier, sans générer de code."
                },
                {"role": "user", "content": composed_prompt}
            ]
        )
        response_text = extract_json(completion.choices[0].message.content)
        if response_text:
            return response_text.strip()
        else:
            print(f"⚠️ Erreur lors de la génération des commentaires pour le fichier {file_name}. Tentative {attempt + 1} sur 3...")
    
    print(f"❌ L'LLM n'a pas réussi à générer les commentaires pour le fichier : {file_name}.")
    return None