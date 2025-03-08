import streamlit as st
import sys
import os
import logging
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.app_generator import AppGenerator
from src.validators.app_validator import AppValidator
from src.generators.get_reformulated_prompt import get_reformulated_prompt
from src.file_manager import get_language_from_extension, is_binary_file, create_zip
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



def main():
    """Main Streamlit application function"""
    load_dotenv()
    
    # Set page config must be the first Streamlit command
    st.set_page_config(page_title="AI Application Generator", layout="wide")
    
    # Initialize session state for multi-step process
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 'initial'
    if 'reformulated_prompt' not in st.session_state:
        st.session_state.reformulated_prompt = ""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'output_path' not in st.session_state:
        st.session_state.output_path = os.path.join(os.getcwd(), "generated_app")
    if 'advanced_options' not in st.session_state:
        st.session_state.advanced_options = {
            'include_tests': False,
            'create_docker': False,
            'add_ci_cd': False,
            'use_sample_json': False,
            'extended_dep_wait': True,
            'is_static_website': False
        }
        
    st.title("AI Application Generator")
    st.markdown("""
    This tool uses AI to generate complete applications based on your description.
    Just provide a detailed description of what you want to build, set the output directory,
    and click "Generate Application".
    """)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    # Create tabs for the different steps
    tabs = st.tabs(["Initial Setup", "Review Requirements", "Generation Progress"])
    
    # Tab 1: Initial Setup
    with tabs[0]:
        if st.session_state.generation_step == "initial":
            st.header("Define Your Application")
            
            user_prompt = st.text_area(
                "Describe the application you want to build", 
                height=150,
                value=st.session_state.user_prompt,
                placeholder="Example: Create a web application that allows users to manage their personal finances. It should track income, expenses, investments, and provide visualizations of spending patterns."
            )
            
            output_path = st.text_input(
                "Output Directory", 
                value=st.session_state.output_path
            )
            
            with st.expander("Advanced Options"):
                is_static_website = st.checkbox("Static website (HTML/CSS/JS only, no backend)", 
                                           value=st.session_state.advanced_options.get('is_static_website', False),
                                           help="Generate a simple static website without a backend server")
                
                include_tests = st.checkbox("Generate tests", 
                                        value=st.session_state.advanced_options.get('include_tests', False))
                
                create_docker = st.checkbox("Create Docker configuration", 
                                        value=st.session_state.advanced_options.get('create_docker', False))
                
                add_ci_cd = st.checkbox("Add CI/CD configuration", 
                                    value=st.session_state.advanced_options.get('add_ci_cd', False))
                
                col1, col2 = st.columns(2)
                with col1:
                    use_sample_json = st.checkbox("Use sample JSON data instead of DB", 
                                              value=st.session_state.advanced_options.get('use_sample_json', False),
                                              help="Generate valid sample JSON data files instead of connecting to a database")
                with col2:
                    extended_dep_wait = st.checkbox("Extended dependency installation time", 
                                               value=st.session_state.advanced_options.get('extended_dep_wait', True),
                                               help="Add extra delay after installing dependencies to ensure they are properly installed")
            
            # Update session state with form values
            st.session_state.user_prompt = user_prompt
            st.session_state.output_path = output_path
            st.session_state.advanced_options = {
                'include_tests': include_tests,
                'create_docker': create_docker,
                'add_ci_cd': add_ci_cd,
                'use_sample_json': use_sample_json,
                'extended_dep_wait': extended_dep_wait,
                'is_static_website': is_static_website
            }
            
            if st.button("Generate Application"):
                if not api_key:
                    st.error("Please enter your OpenAI API key or set it in the .env file.")
                else:
                    if not user_prompt:
                        st.error("Please describe the application you want to build.")
                    elif not output_path:
                        st.error("Please specify an output directory.")
                    else:
                        with st.spinner("Analyzing and reformulating your request..."):
                            # Add static website flag to user prompt if selected
                            prompt_to_process = user_prompt
                            if is_static_website:
                                prompt_to_process = f"[STATIC WEBSITE] {user_prompt}"
                            
                            # Initialize AI client
                            app_generator = AppGenerator(api_key)
                            
                            try:
                                # Get AI-reformulated prompt
                                reformulated_prompt = get_reformulated_prompt(app_generator.api_client, prompt_to_process)
                                logger.info(f"Reformulated prompt received, length: {len(reformulated_prompt)}")
                                
                                # Store in session state
                                st.session_state.reformulated_prompt = reformulated_prompt
                                st.session_state.generation_step = 'review'
                                
                                # Force UI update
                                st.success("✅ Requirements analyzed successfully! Please proceed to the Review tab.")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Error reformulating prompt: {str(e)}")
                                logger.exception("Error reformulating prompt")
        else:
            st.info("You've already completed this step. You can go to the Review Requirements tab.")
            if st.button("Reset and start over"):
                st.session_state.generation_step = 'initial'
                st.session_state.reformulated_prompt = ""
                st.rerun()
    
    # Tab 2: Review Requirements
    with tabs[1]:
        if st.session_state.generation_step == "review":
            st.header("Review AI-Reformulated Requirements")
            st.markdown("Please review the AI-structured version of your request. You can make any necessary edits before proceeding with generation.")
            
            edited_prompt = st.text_area(
                "AI-Structured Requirements", 
                value=st.session_state.reformulated_prompt,
                height=300
            )
            
            # Update session state
            st.session_state.reformulated_prompt = edited_prompt
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Back to Setup"):
                    st.session_state.generation_step = 'initial'
                    st.rerun()
            with col2:
                if st.button("Proceed with Generation ►"):
                    st.session_state.generation_step = 'generating'
                    st.rerun()
        elif st.session_state.generation_step == "initial":
            st.info("Please complete the Initial Setup step first.")
        else:
            st.info("You've already completed this step. You can go to the Generation Progress tab.")

    # Tab 3: Generation Progress
    with tabs[2]:
        if st.session_state.generation_step == "generating":
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
                
                if is_static and not reformulated_prompt.startswith("[STATIC WEBSITE]"):
                    reformulated_prompt = f"[STATIC WEBSITE] {reformulated_prompt}"
                    update_log("Preparing to generate static website (HTML/CSS/JavaScript only)")
                
                # Generate the application
                try:
                    success = app_generator.generate_application(
                        reformulated_prompt,
                        output_path,
                        include_tests=advanced_options['include_tests'],
                        create_docker=advanced_options['create_docker'],
                        add_ci_cd=advanced_options['add_ci_cd'],
                        use_sample_json=advanced_options['use_sample_json']
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
                        
                        validator = AppValidator(app_generator.api_client)
                        validation_success = validator.validate_app(
                            output_path, 
                            app_generator.project_context,
                            extended_dep_wait=advanced_options['extended_dep_wait']
                        )
                        
                        if not validation_success:
                            status_text.text("Application validation failed. Attempting to fix issues...")
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
            
    # Make the right tab active based on current step
    if st.session_state.generation_step == "initial":
        st.session_state.active_tab = 0
    elif st.session_state.generation_step == "review":
        st.session_state.active_tab = 1
    elif st.session_state.generation_step == "generating":
        st.session_state.active_tab = 2

    # Divider for the how it works section
    st.divider()
    st.markdown("### How it works")
    st.markdown("""
    1. **Requirements Analysis**: The system analyzes your description to understand what you want to build.
    2. **Architecture Design**: It designs the overall structure of your application.
    3. **Database Schema**: It creates appropriate database schemas if needed.
    4. **API Design**: It designs API interfaces for the application components.
    5. **Code Generation**: It generates the actual code for the application.
    6. **Code Review**: It reviews the generated code and makes improvements if necessary.
    7. **Project Packaging**: It creates project files like requirements.txt and README.md.
    """)

if __name__ == "__main__":
    main()