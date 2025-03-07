import streamlit as st
import os
from src.utils.file_utils import suggest_directories, create_zip  # Corriger l'import
from src.main_app import AppGenerator
from src.app_validator import AppValidator
import logging

logger = logging.getLogger(__name__)


def show_generation_section(is_reformulation_mode=False):
    """Affiche la section de génération de l'application"""
    st.subheader("Generation Options")

    # Affichage d'informations différentes selon le mode
    if not is_reformulation_mode:
        st.info("You can generate an application directly, or first reformulate your description to get more precise results.")

    # Sélection du répertoire de sortie
    show_directory_selection()

    # Options avancées
    with st.expander("Advanced Options"):
        include_tests = st.checkbox("Generate tests", value=False)
        create_docker = st.checkbox("Create Docker configuration", value=False)
        add_ci_cd = st.checkbox("Add CI/CD configuration", value=False)

    # Bouton de génération avec try/except pour débogage
    try:
        if st.button("Generate Application", key=f"generate_{is_reformulation_mode}"):
            st.info("Processing your request... please wait.")

            # Récupérer le prompt à utiliser (reformulé ou original)
            prompt_to_use = st.session_state.reformulated_prompt if is_reformulation_mode else st.session_state.original_prompt
            app_name = st.session_state.app_name if is_reformulation_mode else None

            # Lancer le processus de génération
            process_generation(
                api_key=st.session_state.api_key,
                prompt=prompt_to_use,
                output_path=st.session_state.output_directory,
                include_tests=include_tests,
                create_docker=create_docker,
                add_ci_cd=add_ci_cd,
                app_name=app_name
            )
    except Exception as e:
        st.error(f"Error when clicking Generate Application: {str(e)}")
        logger.exception("Error in generate button")


def show_directory_selection():
    """Affiche les options de sélection de répertoire"""
    suggested_dirs = suggest_directories()

    col1, col2 = st.columns([3, 1])

    with col1:
        output_path = st.text_input(
            "Output Directory",
            value=st.session_state.output_directory
        )
        # Mise à jour de l'état si modifié
        if output_path != st.session_state.output_directory:
            st.session_state.output_directory = output_path

    with col2:
        if suggested_dirs:
            base_dir = st.selectbox(
                "Base Directory:",
                ["Custom"] + suggested_dirs,
                index=0,
                key="dir_suggestions"
            )

            if base_dir != "Custom" and base_dir != os.path.dirname(st.session_state.output_directory):
                # Mise à jour avec le répertoire sélectionné
                app_name = st.session_state.app_name or "generated_app"
                new_path = os.path.join(
                    base_dir, app_name.replace(" ", "_").lower())
                st.session_state.output_directory = new_path
                st.rerun()  # Utiliser st.rerun() au lieu de st.experimental_rerun()


def process_generation(api_key, prompt, output_path, include_tests=False, create_docker=False, add_ci_cd=False, app_name=None):
    """Gère le processus de génération de l'application"""
    # Vérifications préalables
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
        return

    if not prompt:
        st.error("Please describe the application you want to build.")
        return

    if not output_path:
        st.error("Please specify an output directory.")
        return

    # Remplacer le placeholder APP_NAME par le nom de l'application
    if "**APP_NAME**" in prompt and app_name:
        prompt = prompt.replace("**APP_NAME**", app_name)

    # Préparation de l'interface pour la génération
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Analyzing requirements...")
    progress_bar.progress(10)

    try:
        # Configuration du conteneur de logs
        log_container = st.container()
        log_placeholder = log_container.empty()
        logs = []
        progress_value = 10

        # Fonctions de gestion des logs et de la progression
        def update_log(message):
            logs.append(message)
            log_placeholder.code("\n".join(logs), language="bash")

        def print_override(*args, **kwargs):
            nonlocal progress_value
            message = " ".join(str(arg) for arg in args)
            update_log(message)
            progress_value = min(progress_value + 5, 95)
            progress_bar.progress(progress_value)

        # Initialiser le générateur d'applications
        app_generator = AppGenerator(api_key)

        # Rediriger les outputs
        original_print = print
        app_generator.generate_application.__globals__[
            'print'] = print_override

        try:
            # Créer le répertoire de sortie si nécessaire
            os.makedirs(output_path, exist_ok=True)

            # Générer l'application
            success = app_generator.generate_application(
                prompt,
                output_path,
                include_tests=include_tests,
                create_docker=create_docker,
                add_ci_cd=add_ci_cd,
                app_name=app_name
            )

            # Traiter le résultat
            if success:
                show_successful_generation(
                    app_generator, output_path, status_text, progress_bar)
            else:
                status_text.text("Application generation failed.")
                st.error(
                    "Failed to generate application. Please check the logs for details.")

        except Exception as e:
            logger.exception("Application generation failed")
            raise e
        finally:
            # Restaurer le print original
            app_generator.generate_application.__globals__[
                'print'] = original_print

    except Exception as e:
        progress_bar.progress(100)
        status_text.text("An error occurred during generation.")
        st.error(f"Error: {str(e)}")


def show_successful_generation(app_generator, output_path, status_text, progress_bar):
    """Affiche les résultats après génération réussie"""
    # Validation de l'application générée
    status_text.text("Validating application...")
    validator = AppValidator(app_generator.api_client)
    validation_success = validator.validate_app(
        output_path, app_generator.project_context)

    if not validation_success:
        status_text.text(
            "Application validation failed. Attempting to fix issues...")
        st.warning(
            "Some issues were detected during validation. The system attempted to fix them automatically.")

    # Mise à jour UI
    progress_bar.progress(100)
    st.balloons()
    status_text.text("Application generated successfully!")
    st.success(f"Your application has been generated at: {output_path}")

    # Affichage des fichiers générés
    st.subheader("Generated Files")
    files = []
    for root, dirs, filenames in os.walk(output_path):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    for file in files:
        rel_file = os.path.relpath(file, output_path)
        with st.expander(rel_file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    st.code(f.read(), language="python")
            except UnicodeDecodeError:
                st.warning(
                    f"File {rel_file} contains binary data and cannot be displayed")

    # Option de téléchargement
    st.download_button(
        label="Download as ZIP",
        data=create_zip(output_path),
        file_name="generated_application.zip",
        mime="application/zip"
    )
