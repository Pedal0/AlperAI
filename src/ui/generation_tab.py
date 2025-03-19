import streamlit as st
import traceback
import os
from src.config import AGENT_TEAM_ENABLED

def show_generation_tab(api_key):
    """Display the generation progress tab"""
    if st.session_state.generation_step == "generating":
        # Vérifier si le projet a déjà été généré pour éviter de régénérer
        if 'project_generated' not in st.session_state:
            st.session_state.project_generated = False
            
        # Vérifier si un téléchargement a été effectué
        if 'download_clicked' not in st.session_state:
            st.session_state.download_clicked = False
            
        # Si le téléchargement a été effectué, rediriger vers la page principale
        if st.session_state.download_clicked:
            st.session_state.generation_step = 'initial'
            st.session_state.download_clicked = False
            st.session_state.project_generated = False
            st.rerun()
            return
        
        # Si le projet a déjà été généré, afficher seulement les boutons de téléchargement et de retour
        if st.session_state.project_generated:
            st.success(f"Your application has been generated at: {st.session_state.output_path}")
            
            from src.file_manager import create_zip
            
            # Générer le ZIP une seule fois et le stocker dans la session
            if 'zip_data' not in st.session_state:
                st.session_state.zip_data = create_zip(st.session_state.output_path)
            
            # Utiliser le callback pour marquer le téléchargement
            def on_download_click():
                st.session_state.download_clicked = True
            
            # Afficher le bouton de téléchargement
            st.download_button(
                label="Download as ZIP",
                data=st.session_state.zip_data,
                file_name="generated_application.zip",
                mime="application/zip",
                on_click=on_download_click
            )
            
            # Bouton pour revenir à la page initiale
            if st.button("Start a new project"):
                st.session_state.generation_step = 'initial'
                st.session_state.project_generated = False
                if 'zip_data' in st.session_state:
                    del st.session_state.zip_data
                st.rerun()
            
            return
        
        # Code de génération normal
        from src.generators.app_generator import AppGenerator
        from src.validators.app_validator import AppValidator
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        output_path = st.session_state.output_path
        advanced_options = st.session_state.advanced_options
        
        try:
            app_generator = AppGenerator(api_key)
            
            status_text.text("Analyzing requirements...")
            progress_bar.progress(10)
            
            log_container = st.container()
            log_placeholder = log_container.empty()
            logs = []
            
            progress_value = 10
            
            def update_log(message):
                logs.append(message)
                log_placeholder.code("\n".join(logs), language="bash")
            
            def print_override(*args, **kwargs):
                nonlocal progress_value
                message = " ".join(str(arg) for arg in args)
                update_log(message)
                progress_value = min(progress_value + 5, 95)
                progress_bar.progress(progress_value)
            
            original_print = print
            app_generator.generate_application.__globals__['print'] = print_override
            
            # Process prompt based on static website selection
            reformulated_prompt = st.session_state.reformulated_prompt
            is_static = advanced_options.get('is_static_website', False)
            
            # Ensure proper flags are present in the prompt
            if is_static and not "[STATIC WEBSITE]" in reformulated_prompt:
                reformulated_prompt = f"[STATIC WEBSITE] {reformulated_prompt}"
                update_log("Preparing to generate static website (HTML/CSS/JavaScript only)")
            
            if not "[COMPLETE PROJECT WITH ALL FILES]" in reformulated_prompt:
                reformulated_prompt = f"[COMPLETE PROJECT WITH ALL FILES] {reformulated_prompt}"
                update_log("Ensuring all project files are AI-generated (no templates)")
            
            # Generate the application
            try:
                success = app_generator.generate_application(
                    reformulated_prompt,
                    output_path,
                    include_tests=advanced_options['include_tests'],
                    create_docker=advanced_options['create_docker'],
                    add_ci_cd=advanced_options['add_ci_cd'],
                    use_sample_json=advanced_options['use_sample_json'],
                    ai_generated_everything=True  # Force this option to be true
                )
                
                if success:
                    status_text.text("Validating application...")
                    
                    # Explicitly mark as static website in project context if needed
                    if is_static and isinstance(app_generator.project_context, dict):
                        if 'requirements' not in app_generator.project_context:
                            app_generator.project_context['requirements'] = {}
                        app_generator.project_context['requirements']['is_static_website'] = True
                        
                        if 'technical_stack' not in app_generator.project_context['requirements']:
                            app_generator.project_context['requirements']['technical_stack'] = {}
                            
                        # Fix for the TypeError - check if technical_stack is a dict before setting framework
                        if isinstance(app_generator.project_context['requirements']['technical_stack'], dict):
                            app_generator.project_context['requirements']['technical_stack']['framework'] = 'static'
                        elif isinstance(app_generator.project_context['requirements']['technical_stack'], list):
                            # If it's a list, we need a different approach - add a dict with framework info
                            app_generator.project_context['requirements']['technical_stack'].append({'framework': 'static'})
                        else:
                            # If it's neither a dict nor a list, set it as a dict with framework property
                            app_generator.project_context['requirements']['technical_stack'] = {'framework': 'static'}
                    
                    if AGENT_TEAM_ENABLED:
                        update_log("Lancement de l'équipe d'agents pour vérifier et améliorer le projet...")
                        
                    try:
                        validator = AppValidator(app_generator.api_client)
                        validation_success = validator.validate_app(
                            output_path, 
                            app_generator.project_context,
                            extended_dep_wait=advanced_options['extended_dep_wait']
                        )
                        
                        if not validation_success:
                            status_text.text("Application validation failed. Attempting to fix issues...")
                            if AGENT_TEAM_ENABLED:
                                st.warning("Des problèmes ont été détectés. L'équipe d'agents IA a vérifié et amélioré le projet automatiquement.")
                            else:
                                st.warning("Some issues were detected during validation. The system attempted to fix them automatically.")
                    except Exception as validation_error:
                        status_text.text("Validation encountered errors but the application was generated.")
                        st.warning(f"Validation error: {str(validation_error)}")
                        update_log(f"Warning: Validation process encountered an error: {str(validation_error)}")
                    
                    progress_bar.progress(100)
                    st.balloons()
                    status_text.text("Application generated successfully!")
                    
                    # Marquer le projet comme généré pour éviter de régénérer
                    st.session_state.project_generated = True
                    
                    # Forcer une réexécution pour afficher uniquement les boutons
                    st.rerun()
                else:
                    status_text.text("Application generation failed.")
                    st.error("Failed to generate application. Please check the logs for details.")
                    
                    if st.button("Start Over"):
                        st.session_state.generation_step = 'initial'
                        st.rerun()
                
            finally:
                app_generator.generate_application.__globals__['print'] = original_print
                
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("An error occurred during generation.")
            st.error(f"Error: {str(e)}")
            
            # Add detailed error information for debugging
            error_details = traceback.format_exc()
            with st.expander("Error Details"):
                st.code(error_details)
            
            # Still mark as generated if output_path exists and has files
            if os.path.exists(output_path) and len(os.listdir(output_path)) > 0:
                st.success(f"Despite the error, files were generated at: {output_path}")
                st.session_state.project_generated = True
                
                # Add a download button even when errors occur
                from src.file_manager import create_zip
                try:
                    zip_data = create_zip(output_path)
                    st.download_button(
                        label="Download Generated Files as ZIP",
                        data=zip_data,
                        file_name="generated_application.zip",
                        mime="application/zip"
                    )
                except Exception as zip_error:
                    st.error(f"Could not create ZIP file: {str(zip_error)}")
            
            if st.button("Start Over"):
                st.session_state.generation_step = 'initial'
                st.rerun()
    
    elif st.session_state.generation_step == "initial" or st.session_state.generation_step == "review":
        st.info("Please complete the previous steps first.")