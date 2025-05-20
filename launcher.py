import os
import sys
import subprocess
import hashlib
import time
import socket
from pathlib import Path
import multiprocessing # Ajouté pour freeze_support
import threading # Ajouté pour lancer Flask dans un thread
import requests # Déplacé ici pour une meilleure organisation
import traceback # Pour le logging d\'exception détaillé

# --- Début du bloc de débogage ---
if getattr(sys, 'frozen', False): # Si l\'application est compilée par PyInstaller
    BASE_DIR = Path(sys.executable).resolve().parent
else: # En mode développement
    BASE_DIR = Path(__file__).resolve().parent
LOG_FILE_PATH = BASE_DIR / "launcher_debug.log"

def debug_log(message):
    try:
        with open(LOG_FILE_PATH, "a", encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - PID: {os.getpid()} - {message}\\n")
    except Exception as e:
        print(f"Erreur d\'écriture dans le log de débogage: {e}")
# --- Fin du bloc de débogage ---

# Référence globale à la fonction start_flask_server
start_flask_server_func = None

debug_log(f"--- Nouveau lancement du launcher --- CWD: {os.getcwd()}")
debug_log(f"Python Executable: {sys.executable}")
debug_log(f"sys.argv: {sys.argv}")
debug_log(f"BASE_DIR: {BASE_DIR}")
debug_log(f"LOG_FILE_PATH: {LOG_FILE_PATH}")


try:
    import webview
    debug_log("webview importé avec succès.")
except ImportError as e:
    debug_log(f"Erreur critique: Impossible d'importer webview: {e}\\n{traceback.format_exc()}")
    debug_log("Veuillez vous assurer que pywebview est correctement inclus dans votre fichier .spec (hiddenimports) et que toutes ses dépendances sont présentes.")
    print(f"Erreur critique: Impossible d'importer pywebview: {e}. ")
    print("Veuillez vous assurer que pywebview est correctement inclus dans votre configuration PyInstaller (par exemple, dans hiddenimports dans le fichier .spec).")
    sys.exit(1)

try:
    import run # Pour importer start_flask_server
    debug_log(f"run.py importé avec succès depuis {run.__file__ if hasattr(run, '__file__') else 'unknown location'}.")
    start_flask_server_func = run.start_flask_server # Assigner la fonction ici
except ImportError as e:
    debug_log(f"Erreur: Impossible d\'importer 'run.py': {e}. Tentative d\'ajustement de sys.path.")
    print(f"Erreur: Impossible d\'importer 'run.py': {e}. Assurez-vous qu\'il est dans le même répertoire.")
    # Utiliser BASE_DIR qui est plus fiable, surtout quand gelé
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
        debug_log(f"Ajout de {BASE_DIR} à sys.path.")
    try:
        import run
        debug_log(f"run.py importé avec succès après ajustement de sys.path. Location: {run.__file__ if hasattr(run, '__file__') else 'unknown location'}.")
        start_flask_server_func = run.start_flask_server # Assigner aussi ici après l'ajustement
    except ImportError as e_retry:
        debug_log(f"Erreur critique: Nouvelle tentative d\'import de 'run.py' échouée: {e_retry}\\\\n{traceback.format_exc()}")
        print(f"Nouvelle tentative d\'import de 'run.py' échouée: {e_retry}. Vérifiez la structure de votre projet.")
        sys.exit(1)
    except Exception as e_generic_retry:
        debug_log(f"Erreur critique générique lors de la nouvelle tentative d'import de 'run.py': {e_generic_retry}\\n{traceback.format_exc()}")
        print(f"Erreur générique lors de la nouvelle tentative d'import de 'run.py': {e_generic_retry}.")
        sys.exit(1)


LOCK_FILE = BASE_DIR / "launcher.lock"
debug_log(f"LOCK_FILE path: {LOCK_FILE}")

def file_hash(path):
    if not os.path.exists(path):
        debug_log(f"file_hash: Fichier non trouvé à {path}")
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def update_code():
    debug_log("Entrée dans update_code().")
    try:
        subprocess.run(['git', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        debug_log("Git est installé.")
    except Exception as e:
        debug_log(f"Git non installé ou non trouvé: {e}")
        print("Git n'est pas installé. Veuillez installer git pour activer la mise à jour automatique.")
        return False # Retourner False si git n'est pas là

    req_path_str = 'requirements.txt' # Garder comme string pour file_hash
    req_path = BASE_DIR / req_path_str # Utiliser BASE_DIR pour le chemin complet
    debug_log(f"Chemin requirements.txt: {req_path}")

    req_hash_before = file_hash(req_path)
    debug_log(f"Hash de requirements.txt avant pull: {req_hash_before}")

    print("Vérification des mises à jour sur la branche main...")
    try:
        # Assurez-vous que git opère dans le bon répertoire si nécessaire
        # Pour l'instant, on suppose que CWD est la racine du repo ou que le repo est trouvable par git
        git_pull_cwd = BASE_DIR # Exécuter git pull dans le répertoire de base de l'application
        debug_log(f"Exécution de git fetch/pull dans {git_pull_cwd}")
        subprocess.run(['git', 'fetch'], check=True, timeout=60, cwd=git_pull_cwd)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True, timeout=60, cwd=git_pull_cwd)
        debug_log("Git fetch et pull terminés.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        debug_log(f"Erreur Git lors de la mise à jour: {e}")
        print(f"Erreur Git lors de la mise à jour: {e}")
        return False

    req_hash_after = file_hash(req_path)
    debug_log(f"Hash de requirements.txt après pull: {req_hash_after}")

    if req_hash_before != req_hash_after and req_hash_after is not None:
        debug_log("requirements.txt a changé, réinstallation des dépendances...")
        print("requirements.txt a changé, réinstallation des dépendances...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], check=True, timeout=300)
            debug_log("Dépendances réinstallées.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            debug_log(f"Erreur lors de l'installation des dépendances: {e}")
            print(f"Erreur lors de l'installation des dépendances: {e}")
            return False
    elif req_hash_before is None and req_hash_after is not None:
        debug_log("Nouveau fichier requirements.txt détecté, installation des dépendances...")
        print("Nouveau fichier requirements.txt détecté, installation des dépendances...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], check=True, timeout=300)
            debug_log("Nouvelles dépendances installées.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            debug_log(f"Erreur lors de l'installation des nouvelles dépendances: {e}")
            print(f"Erreur lors de l'installation des nouvelles dépendances: {e}")
            return False
    else:
        debug_log("Pas de changement dans requirements.txt ou fichier non trouvé.")
        print("Pas de changement dans requirements.txt.")
    debug_log("Sortie de update_code().")
    return True

def is_port_in_use(port, host='127.0.0.1'):
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex((host, port)) == 0
        debug_log(f"is_port_in_use({host}:{port}) -> {result}")
        return result
    except socket.error as e:
        debug_log(f"Erreur socket dans is_port_in_use({host}:{port}): {e}")
        return False
    finally:
        if s:
            s.close()

flask_server_thread = None

def start_server_in_thread():
    global flask_server_thread
    debug_log("Entrée dans start_server_in_thread().")
    if is_port_in_use(5000, '127.0.0.1'):
        debug_log("Port 5000 déjà utilisé. Serveur Flask peut-être déjà en cours.")
        print("Le port 5000 est déjà utilisé. Le serveur Flask est peut-être déjà en cours d\'exécution.")
        return True 

    debug_log("Lancement du serveur Flask dans un thread...")
    print("Lancement du serveur Flask dans un thread...")
    
    # S'assurer que start_flask_server_func (la référence globale) est bien appelable
    if not callable(start_flask_server_func):
        debug_log("Erreur critique: start_flask_server_func (de run.py) n'est pas appelable ou n'a pas été initialisé.")
        print("Erreur critique: Impossible de démarrer le serveur Flask car la fonction de démarrage n'a pas pu être chargée.")
        return False

    flask_server_thread = threading.Thread(
        target=start_flask_server_func, # Utiliser la référence globale ici
        args=(5000, '127.0.0.1'), 
        daemon=True
    )
    flask_server_thread.start()
    debug_log(f"Thread serveur Flask démarré (ID: {flask_server_thread.ident}).")
    
    time.sleep(3) # Donner un peu plus de temps au serveur pour démarrer
    if not flask_server_thread.is_alive():
        debug_log("Erreur: Le thread du serveur Flask n'a pas pu démarrer ou s'est arrêté prématurément.")
        print("Erreur: Le thread du serveur Flask n'a pas pu démarrer.")
        return False
    if not is_port_in_use(5000, '127.0.0.1'):
        debug_log("Erreur: Serveur Flask démarré, mais port 5000 non utilisé après 3s.")
        print("Erreur: Le serveur Flask a démarré dans un thread mais le port 5000 n\'est toujours pas utilisé.")
        return False
    debug_log("Serveur Flask démarré avec succès et port vérifié.")
    return True

def open_app():
    debug_log("Entrée dans open_app().")
    server_ready = False
    ping_url = 'http://127.0.0.1:5000/ping'
    debug_log(f"URL de ping: {ping_url}")

    for i in range(30):
        debug_log(f"Tentative de ping {i+1}/30...")
        server_potentially_running = (flask_server_thread and flask_server_thread.is_alive()) or is_port_in_use(5000, '127.0.0.1')
        if not server_potentially_running:
            debug_log("Serveur Flask (thread ou externe) ne semble plus actif. Arrêt des tentatives.")
            print("Le serveur Flask (thread ou externe) ne semble plus actif. Arrêt des tentatives de connexion.")
            return False
        try:
            r = requests.get(ping_url, timeout=1)
            if r.status_code == 200:
                debug_log(f"Ping réussi: {r.status_code} - {r.text}")
                print("Serveur Flask prêt.")
                server_ready = True
                break
            else:
                debug_log(f"Ping échoué avec statut {r.status_code}.")
        except requests.exceptions.ConnectionError:
            debug_log("Ping échoué (ConnectionError).")
        except requests.exceptions.RequestException as e:
            debug_log(f"Ping échoué (RequestException): {e}")
        time.sleep(1)
            
    if not server_ready:
        debug_log("Serveur Flask non prêt après 30 tentatives.")
        print(f"Erreur : le serveur Flask n\'a pas démarré correctement ou n\'est pas joignable à {ping_url}. Arrêt du launcher.")
        return False
        
    debug_log("Ouverture de la fenêtre webview...")
    print("Ouverture de l\'application dans une fenêtre native...")
    try:
        webview.create_window('Bot Project Creator', ping_url.replace("/ping",""), width=1200, height=800, resizable=True) # Pointer vers la racine
        debug_log("Fenêtre webview créée.")
        webview.start(debug=False) # Mettre debug=True pour le développement si nécessaire
        debug_log("webview.start() terminé (fenêtre fermée).")
    except Exception as e:
        debug_log(f"Erreur lors de la création/démarrage de webview: {e}\\n{traceback.format_exc()}")
        print(f"Erreur lors de la création ou du démarrage de la fenêtre webview: {e}")
        return False
    return True

def check_already_running():
    debug_log("Entrée dans check_already_running().")
    if os.path.exists(LOCK_FILE):
        debug_log(f"Fichier de verrouillage {LOCK_FILE} trouvé.")
        try:
            with open(LOCK_FILE, "r") as f:
                pid_str = f.read().strip()
            if not pid_str:
                debug_log("Fichier de verrouillage vide. Suppression...")
                remove_lock_unconditionally()
                return
            pid = int(pid_str)
            debug_log(f"PID dans le fichier de verrouillage: {pid}")
            
            if is_port_in_use(5000, '127.0.0.1'):
                 debug_log(f"Port 5000 utilisé. Une instance (PID {pid} d'après lockfile) semble active. Arrêt.")
                 print(f"Une instance de launcher (PID {pid} d\'après le lockfile) semble déjà en cours car le port 5000 est utilisé. Arrêt.")
                 sys.exit(0)
            else:
                debug_log("Port 5000 non utilisé. Lockfile obsolète. Suppression...")
                remove_lock_unconditionally()
        except ValueError:
            debug_log("Contenu du fichier de verrouillage invalide. Suppression...")
            remove_lock_unconditionally()
        except FileNotFoundError:
            debug_log("Lock file a disparu entre temps.")
            pass 
        except Exception as e:
            debug_log(f"Erreur inattendue lors de la vérification du lockfile: {e}. Suppression...")
            remove_lock_unconditionally()
    else:
        debug_log(f"Aucun fichier de verrouillage trouvé à {LOCK_FILE}.")

    debug_log(f"Création du fichier de verrouillage {LOCK_FILE} pour PID {os.getpid()}.")
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        debug_log("Fichier de verrouillage créé.")
    except IOError as e:
        debug_log(f"AVERTISSEMENT: Impossible de créer le fichier de verrouillage: {e}")
        print(f"AVERTISSEMENT: Impossible de créer le fichier de verrouillage: {e}. L\'application pourrait ne pas fonctionner comme prévu si plusieurs instances sont lancées.")

def remove_lock_unconditionally():
    debug_log(f"Entrée dans remove_lock_unconditionally() pour {LOCK_FILE}.")
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            debug_log(f"Fichier de verrouillage {LOCK_FILE} supprimé (inconditionnellement).")
        except OSError as e:
            debug_log(f"AVERTISSEMENT: Impossible de supprimer {LOCK_FILE} (inconditionnellement): {e}")

def remove_lock():
    debug_log(f"Entrée dans remove_lock() pour {LOCK_FILE}.")
    if os.path.exists(LOCK_FILE):
        try:
            pid_in_file_str = ""
            with open(LOCK_FILE, "r") as f:
                pid_in_file_str = f.read().strip()
            
            if not pid_in_file_str:
                debug_log(f"Fichier de verrouillage {LOCK_FILE} vide. Suppression.")
                os.remove(LOCK_FILE)
            elif pid_in_file_str == str(os.getpid()):
                debug_log(f"Suppression du fichier de verrouillage {LOCK_FILE} (appartient à ce PID).")
                os.remove(LOCK_FILE)
            else:
                debug_log(f"Fichier de verrouillage {LOCK_FILE} appartient à un autre PID ({pid_in_file_str}). Non supprimé.")
        except FileNotFoundError:
            debug_log(f"Fichier de verrouillage {LOCK_FILE} non trouvé lors de la tentative de suppression.")
            pass
        except (IOError, ValueError) as e:
            debug_log(f"AVERTISSEMENT: Erreur lors de la lecture/suppression de {LOCK_FILE}: {e}")
        except Exception as e:
            debug_log(f"AVERTISSEMENT: Erreur inattendue lors de la suppression de {LOCK_FILE}: {e}")
    else:
        debug_log(f"Aucun fichier de verrouillage {LOCK_FILE} à supprimer.")

def main():
    debug_log(f"Entrée dans main() - PID: {os.getpid()}.")
    check_already_running()
    
    update_successful = update_code()
    if not update_successful:
        debug_log("Mise à jour du code échouée. Lancement avec la version actuelle.")
        print("La mise à jour du code a échoué. Lancement avec la version actuelle si possible.")

    server_started_by_us = start_server_in_thread()

    if not server_started_by_us and not is_port_in_use(5000, '127.0.0.1'):
        debug_log("Serveur Flask n'a pas pu être démarré. Arrêt du launcher.")
        print("Le serveur Flask n\'a pas pu être démarré. Arrêt du launcher.")
        sys.exit(1)
    
    debug_log("Serveur démarré ou déjà en cours. Tentative d'ouverture de l'application.")
    app_opened_successfully = open_app()

    if not app_opened_successfully:
        debug_log("L'application n'a pas pu s'ouvrir correctement. Arrêt.")
        print("L\'application n\'a pas pu s\'ouvrir correctement.")
        sys.exit(1)

    debug_log("Fenêtre de l'application fermée par l'utilisateur (ou webview.start() terminé).")
    print("Fenêtre de l\'application fermée.")
    if flask_server_thread is not None and flask_server_thread.is_alive():
        debug_log("Thread serveur Flask actif à la fin de main (après fermeture webview). S'arrêtera car daemon.")
        print("Le thread du serveur Flask est toujours actif et s\'arrêtera avec le programme principal (car daemon).")
    
    debug_log(f"Sortie de main() - PID: {os.getpid()}.")

if __name__ == '__main__':
    # Doit être la première chose dans le bloc if __name__ == '__main__'.
    multiprocessing.freeze_support()
    # Initialiser le log ici pour capturer même les erreurs de freeze_support si possible
    # (bien que freeze_support() lui-même ne devrait pas logger directement ici)
    debug_log(f"--- Script launcher.py démarré dans __main__ (PID: {os.getpid()}) ---")
    debug_log(f"Appel de multiprocessing.freeze_support() terminé.")
    
    try:
        main()
    except SystemExit:
        debug_log(f"SystemExit attrapé dans __main__ (PID: {os.getpid()}).")
        # Pas besoin de re-raise, le finally s'exécutera et le programme se terminera.
    except Exception as e:
        full_traceback = traceback.format_exc()
        debug_log(f"Exception non gérée dans __main__ (PID: {os.getpid()}): {e}\\n{full_traceback}")
        print(f"Une erreur non gérée est survenue dans le launcher: {e}")
    finally:
        debug_log(f"Bloc finally de __main__ atteint (PID: {os.getpid()}). Nettoyage...")
        print("Nettoyage et fermeture du launcher...")
        remove_lock()
        debug_log(f"--- Launcher terminé (PID: {os.getpid()}) ---")
