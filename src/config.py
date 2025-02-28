import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

STRUCTURE_MODEL = "google/gemini-exp-1206:free"  
CODE_MODEL = "cognitivecomputations/dolphin3.0-mistral-24b:free"       

STRUCTURE_SYSTEM_PROMPT = """
Vous êtes un expert en architecture logicielle et en conception de sites web.
Votre rôle est d'analyser la description d'un projet et de créer une structure de fichiers et dossiers optimale.
Répondez uniquement avec un objet JSON représentant la structure du projet.
Les dossiers sont représentés par des objets imbriqués et les fichiers par des paires clé-valeur où la clé est le nom du fichier et la valeur est une brève description.
"""

CODE_SYSTEM_PROMPT = """
Vous êtes un assistant spécialisé dans la génération de code pour des applications.
Répondez uniquement avec le code complet à inclure dans le fichier, sans aucune explication ou commentaire supplémentaire autour du code.
Votre code doit être fonctionnel, bien commenté et suivre les meilleures pratiques.
"""

MAX_RETRIES = 3