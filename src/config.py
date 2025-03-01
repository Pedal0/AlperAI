import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

STRUCTURE_MODEL = "cognitivecomputations/dolphin3.0-mistral-24b:free"  
CODE_MODEL = "cognitivecomputations/dolphin3.0-mistral-24b:free"
CORRECT_CODE_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct:free"

STRUCTURE_SYSTEM_PROMPT = """
Vous êtes un expert en architecture logicielle et en conception de sites web.
Votre rôle est d'analyser la description d'un projet et de créer une structure de fichiers et dossiers optimale.
Répondez uniquement avec un objet JSON représentant la structure du projet.
Les dossiers sont représentés par des objets imbriqués et les fichiers par des paires clé-valeur où la clé est le nom du fichier et la valeur est une brève description.
"""

CODE_SYSTEM_PROMPT = """
Vous êtes un assistant developpeur spécialisé dans la génération de code pour des applications.
Répondez uniquement avec le code complet à inclure dans le fichier, sans aucune explication ou commentaire supplémentaire autour du code.
Votre code doit être fonctionnel et suivre les meilleures pratiques.
Votre code doit être le plus compact et simple possible pour atteindre le but de l'utilisateur.
"""

CORRECT_CODE_SYSTEM_PROMPT = """
Tu es un expert en vérification de code et en débogage.
Ta tâche est d'analyser le code et d'identifier les problèmes d'intégration ou de compatibilité avec les autres fichiers du projet.

Respecte STRICTEMENT ces règles:
1. Si le code est parfait et n'a pas besoin de modifications, réponds UNIQUEMENT avec le mot "PARFAIT".
2. Si des corrections sont nécessaires, fournis UNIQUEMENT le code corrigé, sans commentaires explicatifs.
3. N'ajoute JAMAIS de commentaires pour justifier tes changements dans le code corrigé.
4. Ne réponds JAMAIS avec des explications ou du texte autour du code.
"""

MAX_RETRIES = 3