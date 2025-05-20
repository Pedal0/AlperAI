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
import datetime
import traceback

# Determine base_path for logs and potentially other runtime data
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    base_path_for_logs = Path(sys.executable).parent
else:
    # Running in a normal Python environment
    base_path_for_logs = Path(__file__).resolve().parent

# Importation des utilitaires et configuration
# from src.utils.env_utils import load_env_vars # Sera importé dans start_flask_server

def start_flask_server(port=5000, host='127.0.0.1'):
    """Démarre le serveur Flask et gère le contexte d'exécution."""
    
    if not getattr(sys, 'frozen', False):
        os.chdir(Path(__file__).resolve().parent)

    if not getattr(sys, 'frozen', False):
        project_root_dev = Path(__file__).resolve().parent
        src_dir_path_dev = project_root_dev / "src"
        if str(src_dir_path_dev) not in sys.path:
            sys.path.insert(0, str(src_dir_path_dev))
        if str(project_root_dev) not in sys.path:
            sys.path.insert(0, str(project_root_dev))

    from src.utils.env_utils import load_env_vars
    from app import app # app.py est supposé être à la racine du projet

    # Charger les variables d'environnement
    load_env_vars()

    # Configure logging
    if not app.debug: # Or consider using: if getattr(sys, 'frozen', False):
        import logging
        from logging.handlers import RotatingFileHandler
        
        log_dir = base_path_for_logs / 'logs'
        try:
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / 'app_flask.log'
            # Use a formatter that includes more details for debugging
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
            )
            handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=3) # 2MB per file
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG) # Capture more details

            if not app.logger.handlers: # Avoid adding handler multiple times
                app.logger.addHandler(handler)
            app.logger.setLevel(logging.DEBUG) # Capture more details
            
            app.logger.info("-" * 50)
            app.logger.info(f"Flask logger initialized. Frozen: {getattr(sys, 'frozen', False)}")
            app.logger.info(f"Base path for logs: {base_path_for_logs}")
            app.logger.info(f"Log file: {log_file}")
            app.logger.info(f"CWD at logger setup: {os.getcwd()}")
            app.logger.info(f"sys.executable: {sys.executable}")
            if getattr(sys, 'frozen', False):
                app.logger.info(f"sys._MEIPASS: {sys._MEIPASS}")

        except Exception as e:
            print(f"Critical error setting up Flask logging: {e}")
            try:
                fallback_log_path = base_path_for_logs / "flask_logging_setup_error.log"
                with open(fallback_log_path, "a") as f_err:
                    f_err.write(f"Timestamp: {datetime.datetime.now()}\\n") # Corrected datetime
                    f_err.write(f"Critical error setting up Flask logging: {e}\\n")
                    f_err.write(f"Traceback: {traceback.format_exc()}\\n\\n")
            except Exception:
                pass 

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
    host_arg = '127.0.0.1' 
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            print(f"Le port spécifié '{sys.argv[1]}' n'est pas valide. Utilisation du port par défaut {port_arg}.")
    
    start_flask_server(port=port_arg, host=host_arg)

if __name__ == "__main__":
    main()