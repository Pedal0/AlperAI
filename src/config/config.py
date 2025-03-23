# Configuration pour les modèles d'IA et les limites de tokens

# Modèle par défaut
API_MODEL = "gpt-o1-mini"
API_TEMPERATURE = 0.2

# Ces valeurs sont maintenant définies dans constants.py
# et devraient être importées de là plutôt que redéfinies ici
from .constants import MAX_TOKENS_DEFAULT, MAX_TOKENS_LARGE, MAX_TOKENS_HUGE
