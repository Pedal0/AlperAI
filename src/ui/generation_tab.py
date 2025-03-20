import streamlit as st
import os
import subprocess
import logging
import time
import threading
from src.generators.app_generator import AppGenerator

logger = logging.getLogger(__name__)

def generate_application_thread(options, callback=None):
    """
    Fonction pour générer l'application
    
    Args:
        options: Options de génération (dict)
        callback: Fonction de callback pour les mises à jour de statut (non utilisée)
    """
    try:
        # Initialiser le générateur
        app_generator = AppGenerator(options["api_key"])
        
        # Enregistrer l'état initial dans la session
        if 'generation_logs' not in st.session_state:
            st.session_state.generation_logs = []
        st.session_state.generation_logs.append("Initializing application generator...")
        
        # Lancer la génération
        st.session_state.generation_logs.append("Starting application generation...")
        app_path = app_generator.generate_application(
            user_prompt=options["user_prompt"],
            output_path=options["output_path"],
            include_tests=options["include_tests"],
            create_docker=options["create_docker"],
            add_ci_cd=options["add_ci_cd"],
            use_sample_json=options["use_sample_json"],
            ai_generated_everything=options["ai_generated_everything"]
        )
        
        # Enregistrer le succès dans la session
        st.session_state.generation_logs.append(f"Application generated at: {app_path}")
        st.session_state.generation_logs.append("Generation complete!")
        st.session_state.generation_complete = True
        st.session_state.generation_step = "complete"
        st.session_state.app_path = app_path
    except Exception as e:
        error_msg = f"Error generating application: {str(e)}"
        if 'generation_logs' in st.session_state:
            st.session_state.generation_logs.append(error_msg)
        logger.exception(error_msg)
        st.session_state.generation_error = True
        st.session_state.generation_error_message = error_msg
        st.session_state.generation_step = "review"

def show_generation_tab(api_key):
    """Display the generation progress and results"""
    
    # Si la génération est terminée
    if st.session_state.get("generation_step") == "complete" or st.session_state.get("generation_complete", False):
        st.header("Generation Completed")
        
        # Afficher un message de succès
        st.success("✅ Project successfully generated!")
        
        # Afficher le chemin du projet
        output_path = st.session_state.get('output_path', "Unknown path")
        st.info(f"Project location: `{output_path}`")
        
        # Afficher des commandes utiles
        with st.expander("Useful commands", expanded=True):
            st.code(f"cd {output_path}")
            
            # Ajouter des commandes en fonction du type de projet
            # Détection automatique du type de projet basée sur les fichiers existants
            if os.path.exists(os.path.join(output_path, "requirements.txt")):
                st.session_state.project_type = "python"
                st.code("pip install -r requirements.txt")
                if os.path.exists(os.path.join(output_path, "app.py")):
                    st.code("python app.py")
                elif os.path.exists(os.path.join(output_path, "manage.py")):
                    st.code("python manage.py runserver")
            elif os.path.exists(os.path.join(output_path, "package.json")):
                st.session_state.project_type = "node"
                st.code("npm install")
                st.code("npm start")
        
        # Bouton pour ouvrir le dossier du projet
        if st.button("Open Project Folder"):
            try:
                subprocess.run(['explorer', os.path.normpath(output_path)])
            except Exception as e:
                st.error(f"Error opening directory: {str(e)}")
        
        # Afficher les logs de génération s'ils sont disponibles
        logs = st.session_state.get('generation_logs', [])
        if logs:
            with st.expander("Generation Logs", expanded=True):
                log_text = "\n".join(logs)
                st.text_area("Generation log", value=log_text, height=300, label_visibility="collapsed")
        
        # Vérifier si la vérification par équipe d'agents est activée
        if st.session_state.advanced_options.get("enable_agent_team", False):
            st.subheader("AI Agent Team Verification")
            verification_file = os.path.join(output_path, "verification_complete.txt")
            in_progress_file = os.path.join(output_path, "verification_in_progress.txt")
            
            if os.path.exists(verification_file):
                with st.expander("Verification Results", expanded=True):
                    try:
                        with open(verification_file, 'r', encoding='utf-8') as f:
                            verification_content = f.read()
                        st.success("✅ Verification completed")
                        st.text_area("Details", value=verification_content, height=200, label_visibility="collapsed")
                    except Exception as e:
                        st.error(f"Error reading verification file: {str(e)}")
            elif os.path.exists(in_progress_file):
                st.info("🔄 Agent team verification in progress...")
                st.text("The AI agents are still improving your code. Check back in a few minutes.")
                
                # Ajouter un bouton pour recharger manuellement
                if st.button("Check Verification Status"):
                    st.rerun()
            else:
                st.warning("Agent team verification was enabled but no status file was found.")
        
        # Bouton pour démarrer un nouveau projet
        if st.button("Start New Project"):
            # Réinitialiser l'état de la session pour un nouveau projet
            st.session_state.generation_step = "initial"
            st.session_state.reformulated_prompt = ""
            st.session_state.user_prompt = ""
            st.session_state.generation_logs = []
            st.session_state.generation_complete = False
            if hasattr(st.session_state, 'generation_error'):
                del st.session_state.generation_error
            if hasattr(st.session_state, 'generation_error_message'):
                del st.session_state.generation_error_message
            if hasattr(st.session_state, 'generation_started'):
                del st.session_state.generation_started
            # Rediriger vers l'onglet de définition
            st.rerun()
    
    # Si la génération est en cours
    elif st.session_state.generation_step == "generating":
        st.header("Generating Your Application")
        
        # Démarrer la génération si ce n'est pas déjà fait
        if not st.session_state.get('generation_started', False):
            st.session_state.generation_started = True
            
            # Initialiser les logs
            if 'generation_logs' not in st.session_state:
                st.session_state.generation_logs = []
                
            # Stocker l'heure de début
            st.session_state.start_time = time.time()
            
            if 'generate_options' in st.session_state:
                options = st.session_state.generate_options
                
                # Lancer la génération directement sans thread pour éviter les problèmes de contexte
                generate_application_thread(options)
                
                # Comme la génération est lancée en synchrone, nous devons actualiser manuellement
                st.rerun()
            else:
                st.error("Generation options not found. Please go back to the Review tab.")
                st.session_state.generation_logs.append("Error: Generation options not found")
                st.session_state.generation_step = "review"
                st.rerun()
        
        # Afficher la progression
        with st.container():
            # Afficher l'animation de chargement
            st.markdown("### Generating application...")
            
            # Afficher une barre de progression indéterminée
            progress_bar = st.progress(0)
            for i in range(100):
                # Pour une impression de progression, mais c'est juste visuel
                progress_val = (i % 100) / 100
                progress_bar.progress(progress_val)
                
                # Si la génération est terminée ou une erreur s'est produite, sortir de la boucle
                if st.session_state.get('generation_complete', False) or st.session_state.get('generation_error', False):
                    progress_bar.empty()
                    st.rerun()
                    break
                
                # Éviter de rafraîchir trop souvent pour ne pas surcharger l'interface
                time.sleep(0.1)
            
            # Calculer le temps écoulé
            elapsed_time = time.time() - st.session_state.get('start_time', time.time())
            st.info(f"Time elapsed: {int(elapsed_time)} seconds")
            
            # Afficher les logs actuels
            logs = st.session_state.get('generation_logs', [])
            if logs:
                st.subheader("Generation Progress")
                log_text = "\n".join(logs)
                st.text_area("Generation log", value=log_text, height=300, label_visibility="collapsed")
            
            # Vérifier s'il y a eu une erreur
            if st.session_state.get('generation_error', False):
                st.error(st.session_state.get('generation_error_message', "An error occurred during generation"))
                if st.button("Go back to Review"):
                    st.session_state.generation_step = "review"
                    st.rerun()
            
            # Ajouter un bouton d'annulation
            if st.button("Cancel Generation"):
                st.session_state.generation_step = "review"
                st.session_state.generation_logs.append("Generation cancelled by user")
                st.rerun()
    
    # Si la génération n'a pas encore commencé
    else:
        st.header("Application Generation")
        st.info("Please complete the previous steps first:")
        st.markdown("""
        1. Go to the **Definition** tab to describe your application
        2. Review the reformulated requirements in the **Review** tab
        3. Click the "Generate Application Now" button in the Review tab
        """)