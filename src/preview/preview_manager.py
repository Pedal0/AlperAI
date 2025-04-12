"""
Module de gestion de la prévisualisation d'applications générées.
Contient les fonctions pour lancer, arrêter et gérer les applications générées.
"""
import os
import sys
import json
import time
import signal
import logging
import subprocess
import threading
import platform
import tempfile
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables globales pour stocker les processus en cours d'exécution
running_processes = {}
process_logs = {}
# Dictionnaire pour stocker les ports utilisés par session
session_ports = {}

class ProjectType:
    """Types de projets supportés pour la prévisualisation"""
    FLASK = "flask"
    EXPRESS = "express"
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    STATIC = "static"
    UNKNOWN = "unknown"

def find_free_port(start_port=3000, max_attempts=100):
    """
    Trouve un port disponible en commençant par start_port.
    
    Args:
        start_port (int): Port de départ pour la recherche
        max_attempts (int): Nombre maximum de tentatives
        
    Returns:
        int: Numéro de port disponible ou None si aucun port n'est disponible
    """
    port = start_port
    for _ in range(max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    
    return None

def detect_project_type(project_dir: str) -> str:
    """
    Détecte le type de projet en analysant les fichiers présents.
    
    Args:
        project_dir (str): Chemin du répertoire du projet
        
    Returns:
        str: Type de projet détecté (flask, express, react, vue, angular, static, unknown)
    """
    project_dir = Path(project_dir)
    
    # Vérifier s'il s'agit d'un projet Python/Flask
    if (project_dir / "requirements.txt").exists():
        with open(project_dir / "requirements.txt", "r", encoding="utf-8") as f:
            requirements = f.read().lower()
            if "flask" in requirements:
                return ProjectType.FLASK
    
    if list(project_dir.glob("*.py")):
        # Rechercher des imports Flask dans les fichiers Python
        for py_file in project_dir.glob("**/*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if "import flask" in content or "from flask import" in content:
                        return ProjectType.FLASK
            except:
                pass
    
    # Vérifier s'il s'agit d'un projet Node.js
    if (project_dir / "package.json").exists():
        try:
            with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                package_json = json.load(f)
                dependencies = package_json.get("dependencies", {})
                
                if "express" in dependencies:
                    return ProjectType.EXPRESS
                elif "react" in dependencies or "react-dom" in dependencies:
                    return ProjectType.REACT
                elif "vue" in dependencies:
                    return ProjectType.VUE
                elif "angular" in dependencies or "@angular/core" in dependencies:
                    return ProjectType.ANGULAR
        except:
            pass
    
    # Vérifier s'il s'agit d'un site statique
    if (project_dir / "index.html").exists():
        return ProjectType.STATIC
    
    # Type inconnu par défaut
    return ProjectType.UNKNOWN

def prepare_environment(project_dir: str, project_type: str) -> Tuple[bool, str]:
    """
    Prépare l'environnement d'exécution en fonction du type de projet.
    
    Args:
        project_dir (str): Chemin du répertoire du projet
        project_type (str): Type de projet détecté
        
    Returns:
        Tuple[bool, str]: (Succès, Message ou erreur)
    """
    project_dir = Path(project_dir)
    
    try:
        if project_type == ProjectType.FLASK:
            # Créer un environnement virtuel Python et installer les dépendances
            venv_dir = project_dir / ".venv"
            
            if not venv_dir.exists():
                logger.info(f"Création d'un environnement virtuel Python dans {venv_dir}")
                
                # Utiliser le module venv pour créer l'environnement
                import venv
                venv.create(venv_dir, with_pip=True)
                
                # Chemin vers pip dans l'environnement virtuel
                if platform.system() == "Windows":
                    pip_path = venv_dir / "Scripts" / "pip"
                else:
                    pip_path = venv_dir / "bin" / "pip"
                
                # Installer les dépendances
                requirements_file = project_dir / "requirements.txt"
                if requirements_file.exists():
                    logger.info("Installation des dépendances Python...")
                    subprocess.check_call([str(pip_path), "install", "-r", str(requirements_file)])
                
                return True, "Environnement Python prêt."
            
            return True, "L'environnement Python existe déjà."
            
        elif project_type in [ProjectType.EXPRESS, ProjectType.REACT, ProjectType.VUE, ProjectType.ANGULAR]:
            # Installer les dépendances Node.js
            if (project_dir / "node_modules").exists():
                return True, "Les modules Node.js sont déjà installés."
            
            logger.info("Installation des dépendances Node.js...")
            npm_process = subprocess.Popen(
                ["npm", "install"], 
                cwd=str(project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = npm_process.communicate()
            
            if npm_process.returncode != 0:
                return False, f"Erreur lors de l'installation des dépendances Node.js: {stderr}"
            
            return True, "Dépendances Node.js installées."
            
        elif project_type == ProjectType.STATIC:
            # Rien à préparer pour un site statique
            return True, "Site statique prêt."
            
        else:
            return False, "Type de projet non supporté pour la préparation de l'environnement."
            
    except Exception as e:
        logger.error(f"Erreur lors de la préparation de l'environnement: {str(e)}")
        return False, f"Erreur: {str(e)}"

def get_start_command(project_dir: str, project_type: str, session_id: str = None) -> Tuple[List[str], Optional[Dict]]:
    """
    Détermine la commande pour démarrer l'application.
    
    Args:
        project_dir (str): Chemin du répertoire du projet
        project_type (str): Type de projet détecté
        session_id (str, optional): Identifiant de session pour récupérer le port dynamique
        
    Returns:
        Tuple[List[str], Optional[Dict]]: Commande sous forme de liste et variables d'environnement
    """
    project_dir = Path(project_dir)
    env = os.environ.copy()
    
    if project_type == ProjectType.FLASK:
        # Déterminer l'entrée principale pour Flask
        main_files = ["app.py", "main.py", "server.py", "run.py", "wsgi.py"]
        main_file = None
        
        for file in main_files:
            if (project_dir / file).exists():
                main_file = file
                break
        
        if not main_file:
            # Rechercher un fichier Python contenant app.run() ou Flask
            for py_file in project_dir.glob("*.py"):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "app.run(" in content or "Flask(" in content:
                            main_file = py_file.name
                            break
                except:
                    pass
        
        if not main_file:
            # Utiliser app.py par défaut
            main_file = "app.py"
        
        # Utiliser l'environnement virtuel Python si existant
        venv_dir = project_dir / ".venv"
        if venv_dir.exists():
            if platform.system() == "Windows":
                python_path = str(venv_dir / "Scripts" / "python")
            else:
                python_path = str(venv_dir / "bin" / "python")
        else:
            python_path = sys.executable
        
        return [python_path, str(project_dir / main_file)], env
    
    elif project_type == ProjectType.EXPRESS:
        # Vérifier si un script de démarrage est défini dans package.json
        start_script = None
        
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        # Utiliser npm start
                        return ["npm", "start"], env
                    elif "dev" in scripts:
                        # Utiliser npm run dev
                        return ["npm", "run", "dev"], env
            except:
                pass
        
        # Chercher l'entrée principale
        main_files = ["server.js", "app.js", "index.js"]
        main_file = None
        
        for file in main_files:
            if (project_dir / file).exists():
                main_file = file
                break
        
        if main_file:
            return ["node", str(project_dir / main_file)], env
        else:
            # Utiliser une commande par défaut
            return ["npm", "start"], env
    
    elif project_type == ProjectType.REACT or project_type == ProjectType.VUE or project_type == ProjectType.ANGULAR:
        # Pour les frameworks frontend, utiliser npm start
        return ["npm", "start"], env
    
    elif project_type == ProjectType.STATIC:
        # Pour les sites statiques, nous avons plusieurs options
        
        # Trouver un port disponible
        port = find_free_port()
        if port is None:
            logger.error("Impossible de trouver un port disponible pour le serveur statique")
            port = 3000  # Utiliser 3000 comme fallback, même s'il risque d'échouer
        
        # Mémoriser le port pour cette session
        if session_id:
            session_ports[session_id] = port
            
        # 1. Vérifier si python est disponible
        try:
            # Vérifier si python est installé et disponible
            subprocess.check_output(["python", "--version"], stderr=subprocess.STDOUT)
            # Python est disponible, utiliser le serveur HTTP intégré
            if platform.system() == "Windows":
                # Définir le répertoire de travail directement dans la commande et utiliser un port spécifique
                python_code = """
import http.server
import socketserver

handler = http.server.SimpleHTTPRequestHandler
handler.directory = r'{0}'
socketserver.TCPServer(('0.0.0.0', {1}), handler).serve_forever()
""".format(project_dir, port)
                return ["python", "-c", python_code], env
            else:
                # Pour Linux/Mac, utiliser une approche similaire
                python_code = """
import http.server
import socketserver

handler = http.server.SimpleHTTPRequestHandler
handler.directory = r'{0}'
socketserver.TCPServer(('0.0.0.0', {1}), handler).serve_forever()
""".format(project_dir, port)
                return ["python3", "-c", python_code], env
        except (subprocess.SubprocessError, FileNotFoundError):
            # Python n'est pas disponible, essayons Node.js
            try:
                # Vérifier si node est installé
                subprocess.check_output(["node", "--version"], stderr=subprocess.STDOUT)
                
                # Node est disponible
                try:
                    # Vérifier si npx est disponible
                    subprocess.check_output(["npx", "--version"], stderr=subprocess.STDOUT)
                    # Utiliser npx serve
                    return ["npx", "serve", "-s", str(project_dir), "-p", str(port)], env
                except (subprocess.SubprocessError, FileNotFoundError):
                    # npx n'est pas disponible, mais node oui
                    # On va créer un petit script node pour servir les fichiers statiques
                    http_server_script = """
const http = require('http');
const fs = require('fs');
const path = require('path');
const port = {0};

const mimeTypes = {{
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
  '.woff': 'application/font-woff',
  '.ttf': 'application/font-ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.otf': 'application/font-otf',
  '.wasm': 'application/wasm'
}};

const server = http.createServer((req, res) => {{
  console.log(`${{new Date().toISOString()}} - ${{req.method}} ${{req.url}}`);
  
  // normalize the URL and remove query parameters
  let url = req.url;
  const queryIndex = url.indexOf('?');
  if (queryIndex !== -1) {{
    url = url.substring(0, queryIndex);
  }}
  
  // Normalize URL to serve index.html for '/'
  if (url === '/') {{
    url = '/index.html';
  }}

  // Remove leading slash to get relative file path
  const filePath = path.join(process.cwd(), url);
  
  // Check if the file exists
  fs.stat(filePath, (err, stats) => {{
    if (err) {{
      // If the requested file doesn't exist, try to send index.html for SPA routing
      if (url !== '/index.html') {{
        fs.readFile(path.join(process.cwd(), 'index.html'), (err, data) => {{
          if (err) {{
            res.writeHead(404, {{ 'Content-Type': 'text/plain' }});
            res.end('404 Not Found');
            return;
          }}
          res.writeHead(200, {{ 'Content-Type': 'text/html' }});
          res.end(data);
        }});
        return;
      }}
      
      res.writeHead(404, {{ 'Content-Type': 'text/plain' }});
      res.end('404 Not Found');
      return;
    }}

    // If it's a directory, try to serve the index.html
    if (stats.isDirectory()) {{
      fs.readFile(path.join(filePath, 'index.html'), (err, data) => {{
        if (err) {{
          res.writeHead(404, {{ 'Content-Type': 'text/plain' }});
          res.end('404 Not Found');
          return;
        }}
        res.writeHead(200, {{ 'Content-Type': 'text/html' }});
        res.end(data);
      }});
      return;
    }}

    // Get the file extension to determine MIME type
    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    // Read and serve the file
    fs.readFile(filePath, (err, data) => {{
      if (err) {{
        res.writeHead(500, {{ 'Content-Type': 'text/plain' }});
        res.end('Internal Server Error');
        return;
      }}
      res.writeHead(200, {{ 'Content-Type': contentType }});
      res.end(data);
    }});
  }});
}});

server.listen(port, () => {{
  console.log(`Server running at http://localhost:${{port}}/`);
}});
""".format(port)
                    # Créer un fichier temporaire pour le script
                    temp_dir = tempfile.gettempdir()
                    server_script_path = os.path.join(temp_dir, "simple_http_server.js")
                    
                    with open(server_script_path, "w", encoding="utf-8") as f:
                        f.write(http_server_script)
                    
                    # Exécuter le script Node.js
                    return ["node", server_script_path], env
            except (subprocess.SubprocessError, FileNotFoundError):
                # Ni Python ni Node.js ne sont disponibles
                # Fallback: retourner une commande de serveur statique basique
                # qui échouera probablement, mais avec un message d'erreur utile
                logger.warning("Ni Python ni Node.js ne sont disponibles pour servir des fichiers statiques.")
                if platform.system() == "Windows":
                    return ["python", "-m", "http.server", str(port)], env
                else:
                    return ["python3", "-m", "http.server", str(port)], env
    
    else:
        # Pour les types inconnus, essayer python app.py par défaut
        return [sys.executable, "app.py"], env

def start_preview(project_dir: str, session_id: str) -> Tuple[bool, str, Dict]:
    """
    Démarre la prévisualisation de l'application générée.
    
    Args:
        project_dir (str): Chemin du répertoire du projet
        session_id (str): Identifiant de session pour suivre ce processus
        
    Returns:
        Tuple[bool, str, Dict]: (Succès, Message, Informations supplémentaires)
    """
    if session_id in running_processes:
        stop_preview(session_id)
    
    try:
        # Initialiser le log pour cette session
        process_logs[session_id] = []
        log_entry(session_id, "INFO", f"Démarrage de la prévisualisation pour le projet: {project_dir}")
        
        # Détecter le type de projet
        project_type = detect_project_type(project_dir)
        log_entry(session_id, "INFO", f"Type de projet détecté: {project_type}")
        
        # Préparer l'environnement si nécessaire
        success, message = prepare_environment(project_dir, project_type)
        log_entry(session_id, "INFO" if success else "ERROR", message)
        
        if not success:
            return False, message, {"project_type": project_type}
        
        # Obtenir la commande de démarrage
        command, env = get_start_command(project_dir, project_type, session_id)
        log_entry(session_id, "INFO", f"Commande de démarrage: {' '.join(command)}")
        
        # Démarrer le processus
        process = subprocess.Popen(
            command,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        running_processes[session_id] = {
            "process": process,
            "project_dir": project_dir,
            "project_type": project_type,
            "command": command,
            "start_time": time.time()
        }
        
        # Démarrer les threads pour lire stdout et stderr
        def read_output(stream, log_type):
            for line in stream:
                log_entry(session_id, log_type, line.strip())
            
            if log_type == "ERROR" and not stream.closed:
                stream.close()
        
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "INFO"))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "ERROR"))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Attendre un court instant pour voir si le processus démarre bien
        time.sleep(2)
        
        if process.poll() is not None:
            # Le processus s'est terminé prématurément
            return_code = process.poll()
            log_entry(session_id, "ERROR", f"Le processus s'est terminé avec le code: {return_code}")
            
            # Lire les dernières sorties d'erreur
            remaining_stderr = process.stderr.read()
            if remaining_stderr:
                log_entry(session_id, "ERROR", remaining_stderr)
                
            del running_processes[session_id]
            return False, f"Échec du démarrage du processus (code {return_code})", {
                "project_type": project_type,
                "logs": process_logs.get(session_id, [])
            }
        
        # Déterminer l'URL d'accès à l'application
        app_url = get_app_url(project_type, session_id)
        
        return True, "Application démarrée avec succès", {
            "project_type": project_type,
            "url": app_url,
            "logs": process_logs.get(session_id, []),
            "pid": process.pid
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur: {str(e)}")
        return False, f"Erreur: {str(e)}", {
            "logs": process_logs.get(session_id, [])
        }

def log_entry(session_id: str, level: str, message: str):
    """
    Ajoute une entrée de log pour une session.
    
    Args:
        session_id (str): Identifiant de session
        level (str): Niveau de log (INFO, WARNING, ERROR)
        message (str): Message de log
    """
    if session_id not in process_logs:
        process_logs[session_id] = []
    
    timestamp = time.strftime("%H:%M:%S")
    process_logs[session_id].append({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })
    
    # Limiter le nombre d'entrées
    if len(process_logs[session_id]) > 1000:
        process_logs[session_id] = process_logs[session_id][-1000:]
    
    if level == "ERROR":
        logger.error(f"[{session_id}] {message}")
    elif level == "WARNING":
        logger.warning(f"[{session_id}] {message}")
    else:
        logger.info(f"[{session_id}] {message}")

def get_app_url(project_type: str, session_id: str = None) -> str:
    """
    Retourne l'URL de prévisualisation en fonction du type de projet.
    
    Args:
        project_type (str): Type de projet
        session_id (str, optional): Identifiant de session pour récupérer le port dynamique
        
    Returns:
        str: URL de prévisualisation
    """
    if project_type == ProjectType.FLASK:
        return "http://localhost:5000"
    elif project_type == ProjectType.EXPRESS:
        return "http://localhost:3000"
    elif project_type == ProjectType.REACT:
        return "http://localhost:3000"
    elif project_type == ProjectType.VUE:
        return "http://localhost:8080"
    elif project_type == ProjectType.ANGULAR:
        return "http://localhost:4200"
    elif project_type == ProjectType.STATIC:
        # Utiliser le port dynamique pour les sites statiques si disponible
        if session_id and session_id in session_ports:
            port = session_ports[session_id]
            return f"http://localhost:{port}"
        return "http://localhost:3000"
    else:
        return "http://localhost:5000"  # Par défaut

def stop_preview(session_id: str) -> Tuple[bool, str]:
    """
    Arrête la prévisualisation d'une application.
    
    Args:
        session_id (str): Identifiant de session
        
    Returns:
        Tuple[bool, str]: (Succès, Message)
    """
    if session_id not in running_processes:
        return False, "Aucun processus en cours d'exécution pour cette session"
    
    try:
        process_info = running_processes[session_id]
        process = process_info["process"]
        
        log_entry(session_id, "INFO", "Arrêt de l'application...")
        
        # Envoyer un signal d'interruption au processus
        if platform.system() == "Windows":
            # Sur Windows, utiliser taskkill pour tuer le processus et ses enfants
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            # Sur Unix, utiliser SIGTERM pour une terminaison propre
            process.terminate()
            
            # Attendre un court instant
            time.sleep(1)
            
            # Si le processus est toujours en vie, le tuer
            if process.poll() is None:
                process.kill()
        
        # Attendre que le processus se termine
        process.wait(timeout=5)
        
        log_entry(session_id, "INFO", "Application arrêtée avec succès")
        
        # Conserver les logs mais supprimer le processus
        del running_processes[session_id]
        
        # Supprimer le port utilisé si c'était un site statique
        if session_id in session_ports:
            logger.info(f"Libération du port pour la session {session_id}")
            del session_ports[session_id]
        
        return True, "Application arrêtée avec succès"
        
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur lors de l'arrêt: {str(e)}")
        
        # En cas d'erreur, supprimer quand même l'entrée pour éviter les processus zombies
        if session_id in running_processes:
            del running_processes[session_id]
        
        # Supprimer également l'entrée de port en cas d'erreur
        if session_id in session_ports:
            del session_ports[session_id]
            
        return False, f"Erreur: {str(e)}"

def get_preview_status(session_id: str) -> Dict:
    """
    Récupère le statut actuel de la prévisualisation.
    
    Args:
        session_id (str): Identifiant de session
        
    Returns:
        Dict: Statut de la prévisualisation
    """
    if session_id not in running_processes:
        return {
            "running": False,
            "logs": process_logs.get(session_id, [])
        }
    
    process_info = running_processes[session_id]
    process = process_info["process"]
    
    # Vérifier si le processus est toujours en cours d'exécution
    is_running = process.poll() is None
    
    if not is_running:
        # Le processus s'est terminé
        return_code = process.poll()
        log_entry(session_id, "INFO", f"Le processus s'est terminé avec le code: {return_code}")
        
        # Supprimer le processus de la liste des processus en cours
        del running_processes[session_id]
        
        return {
            "running": False,
            "exit_code": return_code,
            "project_type": process_info["project_type"],
            "project_dir": process_info["project_dir"],
            "logs": process_logs.get(session_id, []),
            "duration": time.time() - process_info["start_time"]
        }
    
    # Le processus est toujours en cours d'exécution
    return {
        "running": True,
        "project_type": process_info["project_type"],
        "project_dir": process_info["project_dir"],
        "url": get_app_url(process_info["project_type"], session_id),
        "logs": process_logs.get(session_id, []),
        "pid": process.pid,
        "duration": time.time() - process_info["start_time"]
    }

def restart_preview(session_id: str) -> Tuple[bool, str, Dict]:
    """
    Redémarre la prévisualisation d'une application.
    
    Args:
        session_id (str): Identifiant de session
        
    Returns:
        Tuple[bool, str, Dict]: (Succès, Message, Informations supplémentaires)
    """
    if session_id not in running_processes:
        return False, "Aucun processus en cours d'exécution pour cette session", {}
    
    project_dir = running_processes[session_id]["project_dir"]
    
    # Arrêter le processus en cours
    success, message = stop_preview(session_id)
    if not success:
        return False, message, {}
    
    # Redémarrer le processus
    return start_preview(project_dir, session_id)

def cleanup_all_processes():
    """
    Nettoie tous les processus en cours d'exécution.
    À appeler lors de l'arrêt de l'application.
    """
    for session_id in list(running_processes.keys()):
        try:
            stop_preview(session_id)
        except:
            pass
    
    # Nettoyer tous les ports restants (au cas où certains n'auraient pas été libérés)
    global session_ports
    if session_ports:
        logger.info(f"Nettoyage final de {len(session_ports)} ports restants")
        session_ports.clear()

def cleanup_unused_ports():
    """
    Nettoie les entrées de port qui ne sont plus associées à des processus en cours d'exécution.
    À appeler périodiquement ou lors de l'arrêt de certaines prévisualisations.
    """
    global session_ports
    
    # Identifier les sessions qui n'ont plus de processus en cours
    sessions_to_remove = [session_id for session_id in session_ports if session_id not in running_processes]
    
    # Supprimer ces entrées du dictionnaire des ports
    for session_id in sessions_to_remove:
        logger.info(f"Nettoyage du port pour la session {session_id}")
        del session_ports[session_id]
    
    if sessions_to_remove:
        logger.info(f"Nettoyage terminé. {len(sessions_to_remove)} ports libérés.")
    
    return len(sessions_to_remove)