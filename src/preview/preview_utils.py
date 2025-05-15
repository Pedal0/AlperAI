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

"""
Module de prévisualisation des applications générées.
Contient les fonctions pour exécuter et afficher les applications.
"""
import re
import time

import subprocess
from pathlib import Path

def parse_readme_instructions(readme_path):
    """
    Parse le README.md pour extraire les instructions d'installation et d'exécution.
    
    Args:
        readme_path (str): Chemin vers le fichier README.md
        
    Returns:
        dict: Dictionnaire contenant les commandes d'installation et d'exécution
    """
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        instructions = {
            'setup_commands': [],
            'run_commands': [],
            'dependencies': [],
            'venv_setup': None,
            'main_file': None
        }
        
        # Recherche de blocs de code avec des instructions d'installation ou de configuration
        code_blocks = re.findall(r'```(?:bash|sh|cmd|batch|\w*\n|\n)(.*?)```', content, re.DOTALL)
        
        for block in code_blocks:
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Identifier les commandes de configuration d'environnement
                if any(venv_cmd in line.lower() for venv_cmd in ['python -m venv', 'virtualenv', 'pipenv']):
                    instructions['venv_setup'] = line
                
                # Identifier les commandes pip install
                elif 'pip install' in line.lower():
                    if 'requirements.txt' in line:
                        instructions['setup_commands'].append(line)
                    else:
                        instructions['dependencies'].append(line)
                
                # Identifier les commandes npm/yarn
                elif any(cmd in line.lower() for cmd in ['npm install', 'yarn add', 'yarn install']):
                    instructions['setup_commands'].append(line)
                
                # Identifier les commandes d'exécution
                elif any(run_cmd in line.lower() for run_cmd in ['python ', 'npm start', 'npm run', 'yarn start', 'flask run', 'streamlit run', 'node ']):
                    instructions['run_commands'].append(line)
                    # Essayer d'extraire le fichier principal pour les applications Python
                    if 'python ' in line.lower() or 'streamlit run' in line.lower():
                        file_match = re.search(r'(?:python|streamlit run)\s+([^\s]+)', line)
                        if file_match:
                            instructions['main_file'] = file_match.group(1)
        
        # Recherche aussi dans le texte normal du README (pas seulement les blocs de code)
        # Cette étape est utile pour les README avec des instructions incomplètes
        if not instructions['setup_commands'] and not instructions['run_commands']:
            # Rechercher des commandes communes dans le texte
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Chercher des commandes d'installation ou d'exécution dans le texte
                if any(cmd in line.lower() for cmd in ['pip install', 'npm install', 'yarn install']) and not line.startswith('#') and not "```" in line:
                    potential_cmd = re.search(r'`([^`]+)`', line)
                    if potential_cmd:
                        cmd_text = potential_cmd.group(1).strip()
                        if 'pip install' in cmd_text.lower():
                            instructions['setup_commands'].append(cmd_text)
                        elif any(install_cmd in cmd_text.lower() for install_cmd in ['npm install', 'yarn install']):
                            instructions['setup_commands'].append(cmd_text)
                
                # Chercher des commandes d'exécution
                if any(cmd in line.lower() for cmd in ['python ', 'npm start', 'flask run', 'node ']) and not line.startswith('#') and not "```" in line:
                    potential_cmd = re.search(r'`([^`]+)`', line)
                    if potential_cmd:
                        cmd_text = potential_cmd.group(1).strip()
                        instructions['run_commands'].append(cmd_text)
                        # Extraire le fichier principal pour Python
                        if 'python ' in cmd_text.lower():
                            file_match = re.search(r'python\s+([^\s]+)', cmd_text)
                            if file_match:
                                instructions['main_file'] = file_match.group(1)
        
        # Si aucune commande de configuration n'est trouvée mais qu'il y a un requirements.txt, ajouter la commande par défaut
        if not any('requirements.txt' in cmd for cmd in instructions['setup_commands']):
            if Path(Path(readme_path).parent / 'requirements.txt').exists():
                instructions['setup_commands'].append('pip install -r requirements.txt')
        
        # Si aucune commande d'exécution n'est trouvée mais qu'il y a un app.py ou main.py, ajouter la commande par défaut
        if not instructions['run_commands']:
            project_dir = Path(readme_path).parent
            potential_main_files = ['app.py', 'main.py', 'index.py', 'server.py']
            for file in potential_main_files:
                if (project_dir / file).exists():
                    instructions['run_commands'].append(f'python {file}')
                    instructions['main_file'] = file
                    break
        
        return instructions
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse du README.md: {e}")
        return {
            'setup_commands': ['pip install -r requirements.txt'] if Path(Path(readme_path).parent / 'requirements.txt').exists() else [],
            'run_commands': [],
            'dependencies': [],
            'venv_setup': None,
            'main_file': None
        }

def setup_virtual_environment(project_dir, venv_command=None):
    """
    Crée et active un environnement virtuel pour le projet.
    
    Args:
        project_dir (str): Chemin vers le répertoire du projet
        venv_command (str, optional): Commande spécifique pour créer l'environnement virtuel
        
    Returns:
        tuple: (succès, chemin_venv ou message d'erreur)
    """
    import sys
    import os
    
    try:
        venv_path = Path(project_dir) / "venv"
        
        # Vérifier si l'environnement virtuel existe déjà
        if venv_path.exists():
            # Vérifier si c'est un environnement valide (présence de python.exe ou python dans bin/Scripts)
            python_exec = venv_path / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")
            if python_exec.exists():
                st.success(f"✅ Environnement virtuel existant détecté à {venv_path}")
                return True, venv_path
            else:
                st.warning(f"⚠️ Dossier venv existant mais incomplet. Suppression et recréation...")
                # Tenter de supprimer le dossier existant
                try:
                    import shutil
                    shutil.rmtree(venv_path)
                except Exception as e:
                    st.error(f"❌ Impossible de supprimer l'environnement virtuel existant: {e}")
                    return False, f"Erreur lors de la suppression de l'environnement virtuel: {e}"
        
        # Si aucune commande spécifique n'est fournie, utiliser la commande par défaut
        if not venv_command:
            venv_command = f'"{sys.executable}" -m venv "{venv_path}"'
        else:
            # Remplacer le placeholder par le chemin réel si nécessaire
            venv_command = venv_command.replace("venv", str(venv_path))
        
        # Créer l'environnement virtuel
        st.info(f"Création de l'environnement virtuel: {venv_command}")
        
        # Exécuter avec capture de sortie pour diagnostic
        result = subprocess.run(
            venv_command, 
            shell=True, 
            cwd=project_dir, 
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            st.error(f"❌ Échec de la création de l'environnement virtuel: {result.stderr}")
            
            # Essayer une approche alternative si la première méthode échoue
            st.info("🔄 Tentative avec une approche alternative...")
            
            # Sur Windows, essayer avec virtualenv si venv échoue
            if os.name == 'nt':
                alt_command = f'pip install virtualenv && virtualenv "{venv_path}"'
                st.info(f"Exécution de: {alt_command}")
                alt_result = subprocess.run(
                    alt_command,
                    shell=True,
                    cwd=project_dir,
                    capture_output=True,
                    text=True
                )
                
                if alt_result.returncode == 0:
                    st.success("✅ Environnement virtuel créé avec virtualenv")
                    return True, venv_path
                else:
                    return False, f"Échec des deux tentatives de création d'environnement virtuel: {alt_result.stderr}"
            
            return False, f"Erreur lors de la création de l'environnement virtuel: {result.stderr}"
        
        # Vérifier que l'environnement a bien été créé
        python_exec = venv_path / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")
        if not python_exec.exists():
            return False, "L'environnement virtuel a été créé mais le binaire Python est introuvable"
        
        return True, venv_path
    
    except subprocess.CalledProcessError as e:
        return False, f"Erreur lors de la création de l'environnement virtuel: {e.stderr}"
    except Exception as e:
        return False, f"Erreur inattendue: {e}"

def install_dependencies(project_dir, commands, venv_path=None):
    """
    Installe les dépendances du projet.
    
    Args:
        project_dir (str): Chemin vers le répertoire du projet
        commands (list): Liste des commandes d'installation
        venv_path (Path, optional): Chemin vers l'environnement virtuel
        
    Returns:
        tuple: (succès, sortie ou message d'erreur)
    """
    import os
    
    try:
        output = []
        
        for cmd in commands:
            # Modifier la commande pour utiliser l'environnement virtuel si disponible
            if venv_path:
                if os.name == 'nt':  # Windows
                    pip_path = venv_path / "Scripts" / "pip"
                    cmd = cmd.replace("pip install", f'"{pip_path}" install')
                else:  # Unix/Linux/Mac
                    pip_path = venv_path / "bin" / "pip"
                    cmd = cmd.replace("pip install", f'"{pip_path}" install')
            
            st.info(f"Exécution: {cmd}")
            process = subprocess.run(
                cmd, 
                shell=True, 
                cwd=project_dir, 
                capture_output=True, 
                text=True
            )
            
            if process.returncode != 0:
                st.warning(f"Commande '{cmd}' a échoué avec le code {process.returncode}")
                st.warning(f"Erreur: {process.stderr}")
                continue
                
            output.append(f"Commande '{cmd}' exécutée avec succès")
            output.append(process.stdout)
        
        # Si au moins une commande a réussi, considérer comme un succès
        if output:
            return True, "\n".join(output)
        else:
            return False, "Toutes les commandes d'installation ont échoué"
    
    except subprocess.CalledProcessError as e:
        return False, f"Erreur lors de l'installation des dépendances: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}"
    except Exception as e:
        return False, f"Erreur inattendue: {e}"

def run_application(project_dir, run_command, venv_path=None):
    """
    Exécute l'application générée.
    
    Args:
        project_dir (str): Chemin vers le répertoire du projet
        run_command (str): Commande pour exécuter l'application
        venv_path (Path, optional): Chemin vers l'environnement virtuel
        
    Returns:
        tuple: (processus, commande)
    """
    import os
    
    try:
        # Modifier la commande pour utiliser l'environnement virtuel si disponible
        if venv_path:
            if os.name == 'nt':  # Windows
                python_path = venv_path / "Scripts" / "python"
                run_command = run_command.replace("python ", f'"{python_path}" ')
                # Ajuster également les commandes Flask et Streamlit
                if "flask" in run_command.lower():
                    flask_path = venv_path / "Scripts" / "flask"
                    run_command = run_command.replace("flask ", f'"{flask_path}" ')
                if "streamlit" in run_command.lower():
                    streamlit_path = venv_path / "Scripts" / "streamlit"
                    run_command = run_command.replace("streamlit ", f'"{streamlit_path}" ')
            else:  # Unix/Linux/Mac
                python_path = venv_path / "bin" / "python"
                run_command = run_command.replace("python ", f'"{python_path}" ')
                # Ajuster également les commandes Flask et Streamlit
                if "flask" in run_command.lower():
                    flask_path = venv_path / "bin" / "flask"
                    run_command = run_command.replace("flask ", f'"{flask_path}" ')
                if "streamlit" in run_command.lower():
                    streamlit_path = venv_path / "bin" / "streamlit"
                    run_command = run_command.replace("streamlit ", f'"{streamlit_path}" ')
        
        # Pour les applications Flask, ajouter le flag pour permettre l'accès depuis l'extérieur
        if "flask run" in run_command and "--host" not in run_command:
            run_command += " --host=0.0.0.0"
        
        # Pour les applications Streamlit, définir un port différent pour éviter les conflits
        if "streamlit run" in run_command and "--server.port" not in run_command:
            run_command += " --server.port=8501"
        
        # Construire les variables d'environnement
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Assurer que Python ne bufférise pas la sortie
        
        # Pour Flask, définir l'environnement de développement
        if "flask" in run_command.lower():
            env["FLASK_ENV"] = "development"
            env["FLASK_DEBUG"] = "1"
        
        # Démarrer le processus
        st.info(f"Démarrage de l'application: {run_command}")
        process = subprocess.Popen(
            run_command,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1  # Ligne par ligne buffering
        )
        
        # Petit délai pour permettre au processus de démarrer
        time.sleep(2)
        
        # Vérifier que le processus est toujours en cours d'exécution
        if process.poll() is not None:
            st.error(f"Le processus s'est terminé prématurément avec le code {process.returncode}")
            # Lire la sortie d'erreur pour diagnostic
            stderr_output = process.stderr.read() if process.stderr else "Pas d'erreur disponible"
            st.error(f"Erreur: {stderr_output}")
            return None, run_command
        
        return process, run_command
    
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de l'application: {e}")
        return None, run_command

def display_preview(project_dir):
    """
    Affiche la prévisualisation d'une application générée.
    
    Args:
        project_dir (str): Chemin vers le répertoire du projet
    """
    # Vide l'interface pour la prévisualisation
    st.empty()  
    
    # Affiche l'en-tête avec un bouton pour revenir
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("📱 Prévisualisation de l'application générée")
    with col2:
        if st.button("⬅️ Retour à l'éditeur", type="primary"):
            from src.preview.preview_manager import toggle_preview_mode
            toggle_preview_mode()
            st.experimental_rerun()
    
    st.divider()
    
    # Analyse le README pour extraire les instructions
    readme_path = Path(project_dir) / "README.md"
    
    if readme_path.exists():
        # Vérifier et améliorer le README si nécessaire
        try:
            from src.preview.steps.improve_readme import improve_readme_for_preview
            improve_readme_for_preview(project_dir)
        except Exception as e:
            import logging
            logging.error(f"Failed to enhance README: {e}")
        
        with st.expander("📝 Instructions du README.md", expanded=True):
            with open(readme_path, 'r', encoding='utf-8') as f:
                st.markdown(f.read())
        
        # Analyse les instructions de configuration
        instructions = parse_readme_instructions(readme_path)
        
        # Conteneur pour la configuration et l'exécution
        setup_container = st.container()
        venv_path = None
        
        with setup_container:
            st.subheader("⚙️ Configuration et démarrage de l'application")
            st.warning("⏱️ Le démarrage peut prendre quelques instants. Veuillez patienter pendant la configuration...")
            
            # Afficher le contenu du dossier pour le débogage
            st.write("📂 Contenu du projet généré:")
            project_files = list(Path(project_dir).glob("*"))
            for file in sorted(project_files, key=lambda x: (x.is_file(), x.name.lower())):
                is_file = file.is_file()
                icon = "📄" if is_file else "📁"
                st.text(f"{icon} {file.name}")
            
            # 1. Configuration de l'environnement virtuel si nécessaire
            if instructions['venv_setup'] or any('requirements.txt' in cmd for cmd in instructions['setup_commands']):
                with st.spinner("Création de l'environnement virtuel... (peut prendre 1-2 minutes)"):
                    success, result = setup_virtual_environment(project_dir, instructions['venv_setup'])
                    if success:
                        venv_path = result
                        st.success("✅ Environnement virtuel créé avec succès")
                    else:
                        st.error(f"❌ Erreur lors de la création de l'environnement virtuel: {result}")
            
            # 2. Installation des dépendances
            if instructions['setup_commands']:
                with st.spinner("Installation des dépendances... (peut prendre 2-5 minutes selon le projet)"):
                    success, output = install_dependencies(project_dir, instructions['setup_commands'], venv_path)
                    if success:
                        st.success("✅ Dépendances installées avec succès")
                        with st.expander("Voir les détails d'installation"):
                            st.code(output)
                    else:
                        st.error(f"❌ Erreur lors de l'installation des dépendances: {output}")
            
            # 3. Exécution de l'application
            if instructions['run_commands']:
                run_command = instructions['run_commands'][0]  # Utilise la première commande d'exécution
                
                st.info(f"🚀 Démarrage de l'application avec la commande: `{run_command}`")
                
                # Vérifie s'il s'agit d'une application web
                is_web_app = any(cmd in run_command.lower() for cmd in ['flask', 'django', 'streamlit', 'npm start', 'node'])
                
                # Démarre le processus d'application
                with st.spinner("Lancement de l'application en cours... (peut prendre 30-60 secondes pour démarrer)"):
                    process, actual_command = run_application(project_dir, run_command, venv_path)
                    st.session_state.app_preview_process = process
                
                if process:
                    # Affiche la sortie de l'application
                    st.success("✅ Application démarrée avec succès")
                    
                    # Ajoute des informations de débogage
                    st.info(f"Commande exécutée: {actual_command}")
                    st.info(f"PID du processus: {process.pid if process else 'N/A'}")
                    
                    # Affiche le cadre de l'application pour les applications web
                    if is_web_app:
                        # Détermine le port à partir de la commande ou utilise les valeurs par défaut
                        port = 8501 if "streamlit" in run_command.lower() else 5000  # Par défaut pour Flask
                        if "--port" in run_command:
                            port_match = re.search(r'--port[\s=](\d+)', run_command)
                            if port_match:
                                port = int(port_match.group(1))
                        elif "port" in run_command:
                            port_match = re.search(r'port[\s=](\d+)', run_command)
                            if port_match:
                                port = int(port_match.group(1))
                        
                        # Attendre un moment pour s'assurer que le serveur démarre
                        st.info(f"Attente du démarrage du serveur sur le port {port}...")
                        time.sleep(8)  # Augmenté à 8 secondes pour donner plus de temps au serveur
                        
                        # Affiche l'iframe pour les applications web
                        st.subheader("🌐 Prévisualisation de l'application web")
                        
                        app_url = f"http://localhost:{port}"
                        st.markdown(f"**URL de l'application:** [Ouvrir dans un nouvel onglet]({app_url})")
                        
                        # Utilise un conteneur pour l'iframe afin de pouvoir le rafraîchir
                        iframe_container = st.container()
                        with iframe_container:
                            st.components.v1.iframe(app_url, height=600, scrolling=True)
                        
                        # Ajouter un bouton de rafraîchissement avec indicateur de temps
                        if st.button("🔄 Rafraîchir l'iframe (si l'application n'apparaît pas)"):
                            st.info("Rafraîchissement de l'iframe...")
                            time.sleep(1)
                            st.experimental_rerun()
                        
                        st.warning("Si l'iframe reste vide après le rafraîchissement, essayez d'ouvrir l'URL directement dans un nouvel onglet.")
                    
                    # Affiche les logs
                    log_container = st.container()
                    with log_container:
                        st.subheader("📋 Logs de l'application")
                        logs_placeholder = st.empty()
                        
                        # Obtient les logs initiaux
                        if process.stdout:
                            # Utiliser une boucle pour collecter plus de logs
                            stdout_lines = []
                            stderr_lines = []
                            
                            # Essayer de lire plusieurs fois pour obtenir plus de logs
                            for attempt in range(3):
                                if not stdout_lines and not stderr_lines:
                                    time.sleep(1)  # Attendre un peu entre les tentatives
                                
                                for _ in range(20):  # Essaie d'obtenir jusqu'à 20 lignes
                                    if process.stdout:
                                        stdout_line = process.stdout.readline()
                                        if stdout_line:
                                            stdout_lines.append(f"STDOUT: {stdout_line}")
                                    if process.stderr:
                                        stderr_line = process.stderr.readline()
                                        if stderr_line:
                                            stderr_lines.append(f"STDERR: {stderr_line}")
                                    # Sortir de la boucle si nous avons collecté suffisamment de logs
                                    if len(stdout_lines) + len(stderr_lines) > 5:
                                        break
                            
                            # Afficher les logs collectés
                            combined_logs = stdout_lines + stderr_lines
                            if combined_logs:
                                logs_placeholder.code("\n".join(combined_logs))
                            else:
                                logs_placeholder.info("Aucun log disponible pour le moment. L'application peut être en cours de démarrage...")
                                
                            # Ajouter un bouton pour mettre à jour les logs
                            if st.button("🔄 Actualiser les logs"):
                                st.experimental_rerun()
                else:
                    st.error(f"❌ Erreur lors du démarrage de l'application")
                    
                    # Suggérer un dépannage
                    st.subheader("🔧 Suggestions de dépannage:")
                    st.write("1. Vérifiez que toutes les dépendances sont installées")
                    st.write("2. Essayez une commande de démarrage alternative")
                    
                    # Proposer des commandes alternatives basées sur le type de projet
                    if any(f.name.lower() == "flask" for f in project_files) or any(f.name.lower() == "app.py" for f in project_files):
                        st.write("Essayez la commande alternative: `flask run` ou `python app.py`")
                        if st.button("▶️ Essayer avec 'flask run'"):
                            process, _ = run_application(project_dir, "flask run", venv_path)
                            st.session_state.app_preview_process = process
                            st.experimental_rerun()
            else:
                st.warning("⚠️ Aucune commande de démarrage n'a été trouvée dans le README.md")
                
                # Essaie de suggérer une commande basée sur la structure du projet
                project_files = list(Path(project_dir).glob("*.py"))
                if project_files:
                    main_candidates = [f for f in project_files if f.stem in ["app", "main", "index", "server"]]
                    if main_candidates:
                        suggested_file = main_candidates[0].name
                        st.info(f"💡 Essayez de lancer l'application avec: `python {suggested_file}`")
                        
                        if st.button("▶️ Lancer avec la commande suggérée"):
                            process, _ = run_application(project_dir, f"python {suggested_file}", venv_path)
                            st.session_state.app_preview_process = process
                            st.experimental_rerun()
    else:
        st.error(f"❌ Aucun fichier README.md trouvé dans le dossier {project_dir}")
        st.warning("Impossible de déterminer les instructions d'installation et de démarrage")
        
        # Essaie de suggérer une façon d'exécuter l'application
        st.subheader("📊 Contenu du dossier généré")
        project_files = list(Path(project_dir).glob("*"))
        for file in sorted(project_files, key=lambda x: (x.is_file(), x.name.lower())):
            is_file = file.is_file()
            icon = "📄" if is_file else "📁"
            st.text(f"{icon} {file.name}")
        
        # Vérifie les points d'entrée courants
        main_files = [f for f in project_files if f.is_file() and f.name.lower() in ["app.py", "main.py", "index.py", "server.py"]]
        if main_files:
            suggested_file = main_files[0].name
            st.info(f"💡 Essayez de lancer l'application avec: `python {suggested_file}`")
            
            if st.button("▶️ Lancer avec la commande suggérée"):
                with st.spinner("Configuration et démarrage... (peut prendre plusieurs minutes)"):
                    venv_success, venv_result = setup_virtual_environment(project_dir)
                    venv_path = venv_result if venv_success else None
                    
                    # Vérifie s'il y a un requirements.txt
                    if Path(project_dir).joinpath("requirements.txt").exists():
                        st.info("Installation des dépendances depuis requirements.txt...")
                        install_dependencies(project_dir, ["pip install -r requirements.txt"], venv_path)
                    
                    process, _ = run_application(project_dir, f"python {suggested_file}", venv_path)
                    st.session_state.app_preview_process = process
                st.experimental_rerun()