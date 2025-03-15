import streamlit as st
from src.config import AGENT_TEAM_ENABLED

def show_generation_tab(api_key):
    """Display the generation progress tab"""
    if st.session_state.generation_step == "generating":
        from src.generators.app_generator import AppGenerator
        from src.validators.app_validator import AppValidator
        from src.file_manager import create_zip
        
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
                        app_generator.project_context['requirements']['technical_stack']['framework'] = 'static'
                    
                    if AGENT_TEAM_ENABLED:
                        update_log("Lancement de l'équipe d'agents pour vérifier et améliorer le projet...")
                        
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
                    
                    progress_bar.progress(100)
                    st.balloons()
                    status_text.text("Application generated successfully!")
                    
                    st.success(f"Your application has been generated at: {output_path}")
                                        
                    st.download_button(
                        label="Download as ZIP",
                        data=create_zip(output_path),
                        file_name="generated_application.zip",
                        mime="application/zip"
                    )
                    
                    if st.button("Start Over"):
                        st.session_state.generation_step = 'initial'
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
            
            if st.button("Start Over"):
                st.session_state.generation_step = 'initial'
                st.rerun()
    
    elif st.session_state.generation_step == "initial" or st.session_state.generation_step == "review":
        st.info("Please complete the previous steps first.")