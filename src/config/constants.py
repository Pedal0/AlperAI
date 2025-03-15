import os

API_MODEL = "gpt-4o-mini"

# Températures par type d'agent
TEMPERATURES = {
    "default": 0.5,
    "requirements": 0.7,     # Plus créatif pour l'analyse des besoins
    "architecture": 0.6,     # Créatif mais structuré
    "database": 0.4,         # Plus précis
    "api": 0.4,              # Plus précis
    "code": 0.2,             # Très précis pour la génération de code
    "review": 0.1,           # Extrêmement précis pour la révision
    "test": 0.3,             # Précis pour les tests
    "css": 0.9,              # Très créatif pour le design CSS
    "reformulation": 0.7,    # Créatif pour la reformulation
    "fixer": 0.2,            # Précis pour la correction d'erreurs
    
    # Températures pour l'équipe d'agents
    "structure_creator": 0.3,  # Précis pour la structure du projet
    "frontend_developer": 0.4, # Balance entre créativité et précision pour le frontend
    "backend_developer": 0.2,  # Très précis pour le backend
    "project_manager": 0.5     # Équilibré pour la coordination
}

# Configuration pour l'équipe d'agents de vérification
AGENT_TEAM_ENABLED = True
AGENT_TEAM_WAIT_TIME = 60  # Temps en secondes à attendre pour que les agents terminent leur travail

MAX_TOKENS_DEFAULT = 6000
MAX_TOKENS_LARGE = 8000
