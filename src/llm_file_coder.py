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
    Génère pour un fichier le code complet à inclure dans ce fichier.
    Elle transmet :
      - le prompt utilisateur décrivant le projet,
      - le nom du fichier actuel,
      - et la structure complète du projet en JSON.
    """
    composed_prompt = (
        f"Question : {user_prompt}\n\n"
        f"Structure du projet (JSON) :\n{json.dumps(project_structure, indent=2)}\n\n"
        f"Fichier actuel : {file_name}\n\n"
        "Génère le code complet pour ce fichier. Réponds uniquement avec le code, sans explication ou commentaire supplémentaire."
    )

    for attempt in range(3):
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-distill-llama-70b:free",
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un assistant spécialisé dans la génération de code pour des applications. Répondez uniquement avec le code complet à inclure dans le fichier, sans aucune explication ou commentaire."
                },
                {"role": "user", "content": composed_prompt}
            ]
        )
        response_text = extract_json(completion.choices[0].message.content)
        if response_text:
            return response_text.strip()
        else:
            print(f"⚠️ Erreur lors de la génération du code pour le fichier {file_name}. Tentative {attempt + 1} sur 3...")
    
    print(f"❌ L'LLM n'a pas réussi à générer le code pour le fichier : {file_name}.")
    return None