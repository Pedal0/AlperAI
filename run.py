#!/usr/bin/env python
"""
Script d'initialisation pour l'application Flask
Initialise les variables d'environnement et lance le serveur
"""

import os
import sys
from pathlib import Path

# Assurez-vous que nous sommes dans le répertoire du projet
project_root = Path(__file__).resolve().parent
os.chdir(project_root)

# Importation des utilitaires et configuration
from src.utils.env_utils import load_env_vars

def main():
    """Fonction principale pour démarrer l'application"""
    # Charger les variables d'environnement
    load_env_vars()
    
    # Importer et lancer l'application Flask
    from app import app
    
    # Vérifier si un port a été spécifié en argument
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Le port spécifié '{sys.argv[1]}' n'est pas valide. Utilisation du port par défaut 5000.")
    
    # Démarrer l'application
    print(f"Démarrage de l'application sur http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    main()