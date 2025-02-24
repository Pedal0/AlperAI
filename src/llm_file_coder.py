import json
import re
from openai import OpenAI
from src.config import OPENROUTER_API_KEY
from src.json_utils import extract_json, normalize_structure

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_file_code(user_prompt, file_name, previous_codes):
    """
    Génère pour un fichier une liste de commentaires concis indiquant ce qu'il
    faudra mettre dans ce fichier. Pour cela, il transmet :
      - le prompt utilisateur décrivant le projet,
      - le nom du fichier actuel,
      - et l'historique des instructions générées pour les autres fichiers.
    """
    context_text = ""
    for fname, code in previous_codes.items():
        context_text += f"Fichier: {fname}\nInstructions:\n{code}\n\n"
    
    composed_prompt = (
        f"{user_prompt}\n\n"
        f"Fichier actuel: {file_name}\n\n"
        f"Instructions des fichiers précédents:\n{context_text}\n\n"
        "Donne-moi une petite liste de commentaires concis (un ou deux points suffisent) "
        "expliquant brièvement ce qu'il faut inclure dans ce fichier. Réponds uniquement avec les commentaires, sans code."
    )
    
    for attempt in range(3):
        completion = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct:free",
            messages=[
                {
                    "role": "system",
                    "content": "Vous êtes un assistant spécialisé dans la génération d'instructions sous forme de commentaires pour la création d'applications. Répondez uniquement avec une liste de commentaires concis décrivant brièvement ce qui doit être présent dans le fichier, sans générer de code."
                },
                {"role": "user", "content": composed_prompt}
            ]
        )
        response_text = extract_json(completion.choices[0].message.content)
        if response_text:
            return response_text.strip()
        else:
            print(f"⚠️ Erreur lors de la génération des instructions pour le fichier {file_name}. Tentative {attempt + 1} sur 3...")
    
    print(f"❌ L'LLM n'a pas réussi à générer les instructions pour le fichier : {file_name}.")
    return None