# Configuration pour les modèles d'IA et les limites de tokens

# Modèle par défaut
API_MODEL = "gpt-3.5-turbo-16k"
API_TEMPERATURE = 0.2

# Limites de tokens pour différentes tailles de génération
MAX_TOKENS_DEFAULT = 10000
MAX_TOKENS_LARGE = 100000  # Pour les générations individuelles
MAX_TOKENS_HUGE = 300000  # Pour les générations multiples en une seule requête
