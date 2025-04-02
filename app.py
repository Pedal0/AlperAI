import streamlit as st
from pathlib import Path
import time

# Import from restructured modules
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.model_utils import is_free_model
from src.api.openrouter_api import call_openrouter_api
from src.utils.file_utils import parse_structure_and_prompt, create_project_structure, parse_and_write_code
from src.utils.prompt_utils import prompt_mentions_design
from src.ui.components import setup_page_config, render_sidebar, render_input_columns, show_response_expander

# --- Interface Streamlit ---

# Setup page configuration
setup_page_config()

# Initialize session state variables
if 'last_api_call_time' not in st.session_state:
    st.session_state.last_api_call_time = 0
if 'last_code_generation_response' not in st.session_state:
    st.session_state.last_code_generation_response = ""
if 'reformulated_prompt' not in st.session_state:
    st.session_state.reformulated_prompt = ""
if 'project_structure' not in st.session_state:
    st.session_state.project_structure = []
if 'process_running' not in st.session_state:
    st.session_state.process_running = False

# Render the UI components
api_key, selected_model = render_sidebar()
user_prompt, target_directory = render_input_columns()

# Bouton de génération principal
generate_button = st.button("🚀 Générer l'application", type="primary", disabled=st.session_state.process_running)

st.markdown("---") # Séparateur visuel

# --- Logique Principale ---
if generate_button and not st.session_state.process_running:
    st.session_state.process_running = True # Empêcher double clic
    valid_input = True
    if not api_key:
        st.error("Veuillez entrer votre clé API OpenRouter dans la barre latérale.")
        valid_input = False
    if not user_prompt:
        st.error("Veuillez décrire l'application que vous souhaitez générer.")
        valid_input = False
    if not target_directory:
        st.error("Veuillez spécifier le chemin du dossier de destination.")
        valid_input = False
    elif not Path(target_directory).is_dir(): # Vérifier si le chemin est un dossier valide
         st.error(f"Le chemin spécifié '{target_directory}' n'est pas un dossier valide ou n'existe pas.")
         valid_input = False

    if valid_input:
        st.session_state.last_code_generation_response = "" # Reset state
        st.session_state.reformulated_prompt = ""
        st.session_state.project_structure = []

        # == ÉTAPE 1: Reformulation et Structure ==
        st.info("▶️ Étape 1: Reformulation du Prompt et Définition de la Structure...")
        status_placeholder_step1 = st.empty() # Pour afficher le statut
        with st.spinner("Appel à l'IA pour reformuler et définir la structure..."):

            # Vérifier le rate limit si modèle gratuit
            if is_free_model(selected_model):
                current_time = time.time()
                time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                    wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                    status_placeholder_step1.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (rate limit)...")
                    time.sleep(wait_time)

            # Construction du prompt pour la première étape
            prompt_step1 = f"""
            Analyze the user's request below. Your tasks are:
            1.  **Reformulate Request:** Create a detailed, precise prompt outlining features, technologies (assume standard web tech like Python/Flask or Node/Express if unspecified, or stick to HTML/CSS/JS if simple), and requirements. This will guide code generation. Include comments in generated code.
            2.  **Define Project Structure:** Propose a complete, logical file/directory structure. List each item on a new line. Use relative paths. Mark directories with a trailing '/'. DO NOT include comments (#) or backticks (```) in the structure list itself.

            User's Request:
            "{user_prompt}"

            Output format MUST be exactly as follows, starting immediately with the first marker:

            ### REFORMULATED PROMPT ###
            [Detailed reformulated prompt here]

            ### STRUCTURE ###
            [List files/folders, one per line, e.g.:
            src/
            src/main.py
            requirements.txt
            README.md]
            """
            messages_step1 = [{"role": "user", "content": prompt_step1}]

            response_step1 = call_openrouter_api(api_key, selected_model, messages_step1, temperature=0.6, max_retries=2)
            st.session_state.last_api_call_time = time.time() # Enregistrer le temps

        if response_step1 and response_step1.get("choices"):
            response_text_step1 = response_step1["choices"][0]["message"]["content"]
            reformulated_prompt, structure_lines = parse_structure_and_prompt(response_text_step1)

            if reformulated_prompt and structure_lines:
                st.session_state.reformulated_prompt = reformulated_prompt
                st.session_state.project_structure = structure_lines
                status_placeholder_step1.success("✅ Étape 1 terminée : Prompt reformulé et structure définie.")

                with st.expander("Voir le Prompt Reformulé et la Structure"):
                    st.subheader("Prompt Reformulé:")
                    st.markdown(f"```text\n{reformulated_prompt}\n```")
                    st.subheader("Structure du Projet Proposée (Nettoyée):")
                    st.code("\n".join(structure_lines), language='text')

                # == ÉTAPE 2: Création de la Structure de Fichiers/Dossiers ==
                st.info("▶️ Étape 2: Création de la Structure Physique...")
                status_placeholder_step2 = st.empty()
                with st.spinner(f"Création des dossiers et fichiers dans '{target_directory}'..."):
                    created_paths = create_project_structure(target_directory, st.session_state.project_structure)

                if created_paths is not None:
                    status_placeholder_step2.success(f"✅ Étape 2 terminée : Structure créée dans '{target_directory}'.")

                    # == ÉTAPE 3: Génération du Code ==
                    st.info("▶️ Étape 3: Génération du Code Complet...")
                    status_placeholder_step3 = st.empty()
                    with st.spinner("Appel à l'IA pour générer le code (cela peut prendre du temps)..."):

                        # Vérifier le rate limit si modèle gratuit
                        if is_free_model(selected_model):
                           current_time = time.time()
                           time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                           if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                               wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                               status_placeholder_step3.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (rate limit)...")
                               time.sleep(wait_time)

                        # --- Ajout de l'instruction pour les animations ---
                        animation_instruction = ""
                        if not prompt_mentions_design(user_prompt):
                             animation_instruction = (
                                 "\n7. **Animation & Fluidity:** Since no specific design was requested, "
                                 "please incorporate subtle CSS animations and transitions (e.g., hover effects, smooth section loading/transitions, subtle button feedback) "
                                 "to make the user interface feel modern, fluid, and engaging. Prioritize usability and avoid overly distracting animations."
                             )
                             st.info("ℹ️ Aucune instruction de design détectée, ajout de la demande d'animations fluides.")

                        # Construction du prompt pour la génération de code
                        prompt_step2 = f"""
                        Generate the *complete* code for the application based on the prompt and structure below.

                        **Detailed Prompt:**
                        {st.session_state.reformulated_prompt}

                        **Project Structure (for reference only):**
                        ```
                        {chr(10).join(st.session_state.project_structure)}
                        ```

                        **Instructions:**
                        1. Provide the full code for *all* files listed in the structure.
                        2. Use the EXACT format `--- FILE: path/to/filename ---` on a line by itself before each file's code block. Start the response *immediately* with the first marker. No introductory text.
                        3. Ensure code is functional, includes imports, basic error handling, and comments.
                        4. For `requirements.txt` or similar, list dependencies.
                        5. For `README.md`, provide setup/run instructions.
                        6. If the code exceeds token limits, end the *entire* response *exactly* with: `GENERATION_INCOMPLETE` (no other text after).{animation_instruction}

                        Generate the code now:
                        """
                        messages_step2 = [{"role": "user", "content": prompt_step2}]

                        # Utiliser une température plus basse pour le code pour moins de créativité/erreurs
                        response_step2 = call_openrouter_api(api_key, selected_model, messages_step2, temperature=0.4, max_retries=2)
                        st.session_state.last_api_call_time = time.time()

                    if response_step2 and response_step2.get("choices"):
                        code_response_text = response_step2["choices"][0]["message"]["content"]
                        st.session_state.last_code_generation_response = code_response_text # Store for display
                        status_placeholder_step3.success("✅ Étape 3 terminée : Réponse de génération de code reçue.")

                        # == ÉTAPE 4: Écriture du Code dans les Fichiers ==
                        st.info("▶️ Étape 4: Écriture du Code dans les Fichiers...")
                        status_placeholder_step4 = st.empty()
                        files_written = []
                        errors = []
                        generation_incomplete = False
                        with st.spinner("Analyse de la réponse et écriture du code..."):
                            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

                        if files_written or errors:
                            status_placeholder_step4.success(f"✅ Étape 4 terminée : Traitement de la réponse terminé.")
                            st.subheader("Résultat de l'écriture des fichiers :")
                            for f in files_written:
                                st.success(f"   📄 Fichier écrit : {Path(f).relative_to(Path(target_directory))}")
                            for err in errors:
                                st.error(f"   ❌ {err}")

                            if not errors and not generation_incomplete:
                                st.success("🎉 Application générée avec succès !")
                                st.balloons()
                            elif generation_incomplete:
                                 st.warning("⚠️ La génération est incomplète. Le code généré jusqu'à présent a été écrit. Vous devrez peut-être ecrire la suite manuellement.")
                            elif errors:
                                st.error("❗️ Des erreurs se sont produites lors de l'écriture de certains fichiers.")

                        else:
                             status_placeholder_step4.error("❌ Étape 4 échouée : Aucun fichier n'a pu être écrit.")


                    else:
                        status_placeholder_step3.error("❌ Étape 3 échouée : Échec de la récupération de la génération de code.")
                        if response_step2: st.json(response_step2) # Afficher la réponse d'erreur si dispo

                else: # Erreur lors de la création de la structure (gérée dans la fonction)
                   status_placeholder_step2.error("❌ Étape 2 échouée : Impossible de créer la structure du projet.")

            else: # Erreur lors du parsing de l'étape 1
                status_placeholder_step1.error("❌ Étape 1 échouée : Impossible d'analyser la réponse de l'IA (prompt/structure).")
                if 'response_text_step1' in locals():
                    with st.expander("Voir la réponse brute de l'Étape 1"):
                        st.code(response_text_step1, language='text')
        else: # Erreur lors de l'appel API de l'étape 1
             status_placeholder_step1.error("❌ Étape 1 échouée : Échec de l'appel API pour la reformulation/structure.")
             if response_step1: st.json(response_step1) # Afficher la réponse d'erreur si dispo

        st.session_state.process_running = False # Réactiver le bouton
        st.info("🏁 Processus terminé.") # Indiquer la fin globale

    else: # Input invalide
        st.session_state.process_running = False # Réactiver le bouton si erreur input

# Show response expander for debugging
show_response_expander()