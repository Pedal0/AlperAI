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
import webview
import base64 # Ajouté pour le décodage des données du fichier

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


# Fonction pour sauvegarder les données reçues de JavaScript
def save_file_via_dialog(filename_suggestion, data_base64):
    debug_log(f"Entrée dans save_file_via_dialog. Suggestion de nom: {filename_suggestion}")
    try:
        if not webview.windows:
            debug_log("Erreur critique dans save_file_via_dialog: Aucune fenêtre webview active (webview.windows est vide).")
            return {"success": False, "error": "No active webview window found to open save dialog."}

        current_window = webview.windows[0] # Accéder à la fenêtre active

        # Ouvrir la boîte de dialogue "Enregistrer sous"
        # Utiliser un répertoire par défaut comme le dossier Téléchargements de l'utilisateur
        default_dir = str(Path.home() / "Downloads")
        if not os.path.exists(default_dir):
            default_dir = str(Path.home()) # Fallback au dossier home si Downloads n\'existe pas

        # Corrected: Call create_file_dialog on the window instance
        if not webview.windows:
            debug_log("Erreur: Aucune fenêtre webview active trouvée pour create_file_dialog.")
            return {"success": False, "error": "No active webview window."}
        
        active_window = webview.windows[0]
        # For SAVE_DIALOG, create_file_dialog returns a string path or None
        file_path_str = active_window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=default_dir,
            save_filename=filename_suggestion
        )

        # Check if a valid file path string was returned
        if file_path_str and isinstance(file_path_str, str):
            try:
                debug_log(f"Tentative d'écriture dans le fichier : {file_path_str}")
                # Decode the base64 data
                file_data = base64.b64decode(data_base64)
                
                # Write the data to the selected file
                with open(file_path_str, 'wb') as f:
                    f.write(file_data)
                
                debug_log(f"Fichier sauvegardé avec succès : {file_path_str}")
                return {"success": True, "path": file_path_str}
            except Exception as e:
                error_message = f"Erreur lors de la sauvegarde du fichier : {e}"
                debug_log(error_message)
                return {"success": False, "error": error_message}
        else:
            debug_log("Boîte de dialogue de sauvegarde annulée ou fermée, ou chemin invalide.")
            return {"success": False, "error": "Save dialog cancelled or closed, or invalid path."}

    except Exception as e:
        error_msg = f"Erreur dans save_file_via_dialog: {str(e)}"
        debug_log(f"{error_msg}\\n{traceback.format_exc()}")
        return {"success": False, "error": error_msg}

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

    for i in range(30): # Tenter pendant 30 secondes max
        debug_log(f"Tentative de ping {i+1}/30...")
        try:
            response = requests.get(ping_url, timeout=1)
            if response.status_code == 200:
                debug_log(f"Ping réussi: {response.status_code} - {response.text.strip()}")
                server_ready = True
                break
            else:
                debug_log(f"Ping échoué (status {response.status_code}). Réessai dans 1s...")
        except requests.ConnectionError:
            debug_log("Ping échoué (ConnectionError). Réessai dans 1s...")
        except requests.Timeout:
            debug_log("Ping échoué (Timeout). Réessai dans 1s...")
        except Exception as e:
            debug_log(f"Ping échoué (Exception: {e}). Réessai dans 1s...")
        time.sleep(1)

    if not server_ready:
        debug_log("Serveur Flask non prêt après 30s. Impossible d'ouvrir la fenêtre webview.")
        print("Le serveur Flask n'a pas pu démarrer correctement. Impossible d'ouvrir l'application.")
        return False # Indicate failure

    debug_log("Ouverture de la fenêtre webview...")
    try:
        window = webview.create_window(
            'Bot Project Creator',
            'http://127.0.0.1:5000',
            width=1200, 
            height=800,
            resizable=True
            # confirm_close=True # Removed to prevent quit confirmation
        )
        debug_log("Fenêtre webview créée.")

        # Exposer la fonction Python à JavaScript
        try:
            window.expose(save_file_via_dialog)
            debug_log("Fonction 'save_file_via_dialog' exposée à JavaScript.")
        except Exception as e_expose:
            debug_log(f"Erreur lors de l'exposition de la fonction à JavaScript: {e_expose}\\n{traceback.format_exc()}")
            # Continuer même si l'exposition échoue, bien que le téléchargement ne fonctionnera pas

        # Supprimer les anciens gestionnaires d'événements de téléchargement car ils ne fonctionnent pas
        # if hasattr(window, 'events') and hasattr(window.events, 'download'):
        # debug_log("Tentative de suppression du gestionnaire window.events.download (s'il existe).")
        # try:
        # window.events.download -= on_download_requested # Assurez-vous que on_download_requested est défini ou supprimez cette ligne
        # except Exception as e_remove_event:
        # debug_log(f"Erreur lors de la suppression de l'ancien gestionnaire d'événements: {e_remove_event}")
        # else:
        # debug_log("Aucun gestionnaire d'événements de téléchargement standard trouvé sur l'objet window.")


        # Try to explicitly use Edge WebView2 (mswebview2)
        # CEF is causing Python version compatibility issues.
        webview.start(gui='mswebview2') # Removed debug=True
        debug_log("webview.start() terminé (fenêtre fermée).")
        return True # Indicate success
    except Exception as e:
        debug_log(f"Erreur lors de la création ou du démarrage de la fenêtre webview: {e}\\\\n{traceback.format_exc()}")
        print(f"Erreur lors de l'ouverture de l'application: {e}")
        return False # Indicate failure

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
    # update_code() retourne False si git n'est pas là ou si une erreur survient.
    # On continue même si la mise à jour échoue, mais on logue.
    if not update_successful:
        debug_log("Mise à jour du code non effectuée ou échouée. Lancement avec la version actuelle.")
        # print("La mise à jour du code a échoué ou n'a pas été effectuée. Lancement avec la version actuelle si possible.")

    server_started_by_us = start_server_in_thread()

    if not server_started_by_us and not is_port_in_use(5000, '127.0.0.1'):
        debug_log("Serveur Flask n'a pas pu être démarré. Arrêt du launcher.")
        print("Le serveur Flask n\\\'a pas pu être démarré. Arrêt du launcher.")
        sys.exit(1) # Quitter si le serveur ne peut pas démarrer
    
    debug_log("Serveur démarré ou déjà en cours. Tentative d'ouverture de l'application.")
    app_opened_successfully = open_app() # Stocker le résultat de open_app()

    if not app_opened_successfully: # Vérifier le booléen retourné
        debug_log("L'application n'a pas pu s'ouvrir correctement (open_app a retourné False). Arrêt.")
        print("L\\\'application n\\\'a pas pu s\\\'ouvrir correctement.")
        # Ne pas appeler sys.exit(1) ici si open_app gère déjà la sortie en cas d'erreur critique
        # ou si on veut que le finally s'exécute proprement.
        # Si open_app retourne False à cause d'une exception pendant webview.start, le programme va continuer ici.
        # Si l'utilisateur ferme la fenêtre, open_app retourne True.
        # Si une exception survient avant webview.start, open_app retourne False.
        # Le sys.exit(1) est déplacé dans le bloc except de main pour les erreurs non gérées.
    else:
        debug_log("Fenêtre de l'application fermée par l'utilisateur ou webview.start() terminé normalement.")
        print("Fenêtre de l\\\'application fermée.")

    # Le reste du code de main s'exécute après la fermeture de la fenêtre ou si open_app a échoué avant webview.start()
    # Si flask_server_thread est un daemon, il s'arrêtera avec le thread principal.
    if flask_server_thread is not None and flask_server_thread.is_alive():
        debug_log("Thread serveur Flask actif à la fin de main (après fermeture webview ou échec open_app). S'arrêtera car daemon.")
        # print("Le thread du serveur Flask est toujours actif et s\\\'arrêtera avec le programme principal (car daemon).")
    
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
