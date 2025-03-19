import streamlit as st
import os
import logging

logger = logging.getLogger(__name__)

def show_initial_setup_tab(api_key):
    """Display the initial setup tab"""
    if st.session_state.generation_step == "initial":
        st.header("Define Your Application")
        
        # Show API key status
        if not api_key:
            st.warning("No OpenAI API key found in environment. Make sure to set OPENAI_API_KEY in your .env file.")
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                st.error("No OpenRouter API key found either. You must set at least one API key in your .env file.")
            else:
                st.success("OpenRouter API key found in environment.")
        else:
            st.success("OpenAI API key found in environment.")
        
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
        
        show_advanced_options()
        
        # Update session state with form values
        st.session_state.user_prompt = user_prompt
        st.session_state.output_path = output_path
        
        handle_generate_button(api_key)
    else:
        st.info("You've already completed this step. You can go to the Review Requirements tab.")
        if st.button("Reset and start over"):
            st.session_state.generation_step = 'initial'
            st.session_state.reformulated_prompt = ""
            st.rerun()

def show_advanced_options():
    """Display advanced options expandable section"""
    with st.expander("Advanced Options"):
        use_openrouter = st.checkbox("Use OpenRouter API (for non-agent team AI calls)", 
                               value=st.session_state.advanced_options.get('use_openrouter', True),
                               help="Use OpenRouter API with Gemini model instead of direct OpenAI API")
                               
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
    
    # Update session state with advanced options
    st.session_state.advanced_options = {
        'use_openrouter': use_openrouter,  # New option for OpenRouter
        'include_tests': include_tests,
        'create_docker': create_docker,
        'add_ci_cd': add_ci_cd,
        'use_sample_json': use_sample_json,
        'extended_dep_wait': extended_dep_wait,
        'is_static_website': is_static_website,
        'ai_generated_everything': True  # Always keep this true
    }

def handle_generate_button(api_key):
    """Handle the Generate Application button"""
    from src.generators.app_generator import AppGenerator
    from src.generators.get_reformulated_prompt import get_reformulated_prompt
    
    if st.button("Generate Application"):
        if not api_key:
            st.error("Please enter your OpenAI API key or set it in the .env file.")
        else:
            if not st.session_state.user_prompt:
                st.error("Please describe the application you want to build.")
            elif not st.session_state.output_path:
                st.error("Please specify an output directory.")
            else:
                with st.spinner("Analyzing and reformulating your request..."):
                    # Add static website flag to user prompt if selected
                    prompt_to_process = st.session_state.user_prompt
                    if st.session_state.advanced_options['is_static_website']:
                        prompt_to_process = f"[STATIC WEBSITE] {prompt_to_process}"
                    
                    # Add flag to ensure all files are AI-generated
                    prompt_to_process = f"[COMPLETE PROJECT WITH ALL FILES] {prompt_to_process}"
                    
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