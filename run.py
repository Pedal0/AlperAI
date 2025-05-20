# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

#!/usr/bin/env python
"""
Script d'initialisation pour l'application Flask
Initialise les variables d'environnement et lance le serveur
"""

import os
import sys
from pathlib import Path

# Importation des utilitaires et configuration
# from src.utils.env_utils import load_env_vars # Sera importé dans start_flask_server

def start_flask_server(port=5000, host='127.0.0.1'):
    """Démarre le serveur Flask et gère le contexte d'exécution."""
    project_root = Path(__file__).resolve().parent
    
    # S'assurer que le CWD est la racine du projet si ce n'est pas déjà le cas
    if str(project_root) != os.getcwd():
        os.chdir(project_root)

    # S'assurer que 'src' et la racine du projet sont dans sys.path pour les importations
    # Cela est important si launcher.py et run.py sont à la racine du projet.
    src_dir_path = project_root / "src"
    if str(src_dir_path) not in sys.path:
        sys.path.insert(0, str(src_dir_path))
    if str(project_root) not in sys.path: # Pour 'from app import app'
        sys.path.insert(0, str(project_root))

    from src.utils.env_utils import load_env_vars
    from app import app # app.py est supposé être à la racine du projet

    # Charger les variables d'environnement
    load_env_vars()
    
    # Démarrer l'application
    print(f"Démarrage de l'application Flask sur http://{host}:{port}")
    try:
        # Utiliser 127.0.0.1 pour le serveur Flask lorsqu'il est utilisé avec pywebview
        # pour des raisons de sécurité et de simplicité.
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except SystemExit:
        # Werkzeug peut lever SystemExit lors d'un signal d'arrêt (ex: Ctrl+C dans le terminal direct)
        print("Le serveur Flask a été arrêté.")
    except Exception as e:
        print(f"Erreur lors de l'exécution du serveur Flask: {e}")
        # Gérer d'autres erreurs potentielles ici

def main():
    """Fonction principale pour démarrer l'application (quand run.py est exécuté directement)"""
    port_arg = 5000
    # Pour une exécution directe, 0.0.0.0 peut être utilisé pour rendre accessible sur le réseau local.
    # Cependant, pour l'utilisation avec le launcher, 127.0.0.1 est préférable.
    host_arg = '0.0.0.0' 
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            print(f"Le port spécifié '{sys.argv[1]}' n'est pas valide. Utilisation du port par défaut {port_arg}.")
    
    start_flask_server(port=port_arg, host=host_arg)

if __name__ == "__main__":
    main()