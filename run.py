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
import logging
from logging.handlers import RotatingFileHandler

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

    from src.utils.env_utils import load_env_vars
    from app import app # app.py est supposé être à la racine du projet

    # Charger les variables d'environnement
    load_env_vars()

    # Configure basic logging for UTF-8 console output
    # This might help with Werkzeug and other root logger outputs
    # Ensure this is called before Flask/Werkzeug initializes its own logging too much
    # Remove existing root handlers if any, to avoid duplicate console logs if re-running this
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler(sys.stdout) # Explicitly use sys.stdout
                        ])
    
    # Ensure all stream handlers for the root logger use UTF-8
    # This is a bit more forceful for console.
    for handler in logging.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            try:
                handler.stream.reconfigure(encoding='utf-8') # Python 3.7+
            except AttributeError:
                # For older versions or if reconfigure is not available on this stream
                # Fallback or accept potential issues if this stream is the console
                # and PYTHONIOENCODING is not set.
                pass


    # Configure logging for the Flask app (file handler)
    log_dir = base_path_for_logs / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / 'app_flask.log'

    # Remove any pre-existing handlers from app.logger to avoid conflicts/duplicates
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)

    # Create a new file handler with UTF-8 encoding
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=1024 * 1024 * 5,  # 5 MB
        backupCount=5,
        encoding='utf-8'  # Explicitly set UTF-8
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO) # Ensure app logger level is set
    app.logger.propagate = False # Prevent app logs from going to root logger's console handler

    app.logger.info(f"Flask logger (re)initialized. Log file: {log_file_path} (UTF-8)")
    app.logger.info(f"Base path for logs: {base_path_for_logs}")

    # Démarrer l'application
    print(f"Démarrage de l'application Flask sur http://{host}:{port}")
    try:
        # Use app.debug setting from Flask app instance if configured, or pass explicitly.
        # Logs indicate debug mode is off, so matching that.
        app.run(host=host, port=port, debug=app.debug)
    except SystemExit:
        app.logger.info("Flask application exited via SystemExit.")
    except Exception as e:
        app.logger.exception("An error occurred during Flask app execution:")
    finally:
        app.logger.info("Flask application shutdown.")

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