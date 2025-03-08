import streamlit as st
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.generators.app_generator import AppGenerator
from src.validators.app_validator import AppValidator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def get_language_from_extension(file_path):
    """Determine the appropriate language for syntax highlighting based on file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'bash',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.tsx': 'typescript',
        '.ts': 'typescript',
        '.jsx': 'javascript'
    }
    return language_map.get(ext, 'text')

def is_binary_file(file_path):
    """Check if a file is likely to be binary rather than text"""
    binary_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.ico', '.pdf', '.zip', '.tar', 
                         '.gz', '.exe', '.dll', '.so', '.pyc', '.ttf', '.woff']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in binary_extensions

def create_zip(directory):
    """Create a ZIP archive of the directory"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(
                    file_path, 
                    os.path.relpath(file_path, os.path.join(directory, '..'))
                )
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def get_reformulated_prompt(api_client, user_prompt):
    """Use AI to reformat and structure the user's prompt"""
    import json
    
    reformulation_prompt = """
    You are a requirements refinement expert. Your task is to take the user's application description 
    and reformulate it into a clear, structured, and detailed specification.
    
    Format the output as a comprehensive description that covers:
    1. The main purpose of the application
    2. Key features and functionality
    3. User types/roles if applicable
    4. Data requirements and storage needs
    5. Any specific technical requirements mentioned
    
    Make sure to preserve ALL details from the original prompt but organize them better.
    Do NOT add major new features that weren't implied in the original.
    
    Return ONLY the reformulated description, without any explanations or metadata.
    """
    
    response = api_client.call_agent(reformulation_prompt, user_prompt, max_tokens=1000)
    return response.strip() if response else user_prompt

def main():
    """Main Streamlit application function"""
    load_dotenv()
    
    # Check if page was reloaded and reset state if needed
    query_params = st.experimental_get_query_params()
    if "reloaded" not in query_params:
        # Set a parameter to detect future reloads
        st.experimental_set_query_params(reloaded='true')
    else:
        # Page was reloaded, reset all states to initial
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    # Initialize session state for multi-step process
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 'initial'  # Possible values: 'initial', 'review', 'generating'
    if 'reformulated_prompt' not in st.session_state:
        st.session_state.reformulated_prompt = ""
    if 'advanced_options' not in st.session_state:
        st.session_state.advanced_options = {
            'include_tests': False,
            'create_docker': False,
            'add_ci_cd': False,
            'use_sample_json': False,
            'extended_dep_wait': True,
            'is_static_website': False
        }
        
    st.set_page_config(page_title="AI Application Generator", layout="wide")
    
    st.title("AI Application Generator")
    st.markdown("""
    This tool uses AI to generate complete applications based on your description.
    Just provide a detailed description of what you want to build, set the output directory,
    and click "Generate Application".
    """)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    # Input fields are only shown in the initial step
    if st.session_state.generation_step == 'initial':
        user_prompt = st.text_area("Describe the application you want to build", 
                                height=150,
                                placeholder="Example: Create a web application that allows users to manage their personal finances. It should track income, expenses, investments, and provide visualizations of spending patterns.")
        
        output_path = st.text_input("Output Directory", 
                                value=os.path.join(os.getcwd(), "generated_app"))
        
        with st.expander("Advanced Options"):
            # Add option to specify static website
            is_static_website = st.checkbox("Static website (HTML/CSS/JS only, no backend)", value=False, 
                                         help="Generate a simple static website without a backend server")
            
            include_tests = st.checkbox("Generate tests", value=False)
            create_docker = st.checkbox("Create Docker configuration", value=False)
            add_ci_cd = st.checkbox("Add CI/CD configuration", value=False)
            col1, col2 = st.columns(2)
            with col1:
                use_sample_json = st.checkbox("Use sample JSON data instead of DB", value=False, 
                                            help="Generate valid sample JSON data files instead of connecting to a database")
            with col2:
                extended_dep_wait = st.checkbox("Extended dependency installation time", value=True,
                                            help="Add extra delay after installing dependencies to ensure they are properly installed")
        
        # Store advanced options in session state to preserve them across steps
        st.session_state.advanced_options = {
            'include_tests': include_tests,
            'create_docker': create_docker,
            'add_ci_cd': add_ci_cd,
            'use_sample_json': use_sample_json,
            'extended_dep_wait': extended_dep_wait,
            'is_static_website': is_static_website
        }
        
        # Store output path in session state
        st.session_state.output_path = output_path
                
        if st.button("Generate Application"):
            if not api_key:
                st.error("Please enter your OpenAI API key or set it in the .env file.")
                return
                
            if not user_prompt:
                st.error("Please describe the application you want to build.")
                return
                
            if not output_path:
                st.error("Please specify an output directory.")
                return
            
            # Add static website flag to user prompt if selected
            if is_static_website:
                user_prompt = f"[STATIC WEBSITE] {user_prompt}"
                
            # Initialize AI client to get reformulated prompt
            app_generator = AppGenerator(api_key)
            
            with st.spinner("Analyzing and reformulating your request..."):
                # Get AI-reformulated prompt
                reformulated_prompt = get_reformulated_prompt(app_generator.api_client, user_prompt)
                st.session_state.reformulated_prompt = reformulated_prompt
                st.session_state.generation_step = 'review'
                st.rerun()
    
    # Review step - show reformulated prompt and allow editing
    elif st.session_state.generation_step == 'review':
        st.subheader("Review AI-Reformulated Requirements")
        st.markdown("Please review the AI-structured version of your request. You can make any necessary edits before proceeding with generation.")
        
        edited_prompt = st.text_area("AI-Structured Requirements", 
                                    value=st.session_state.reformulated_prompt,
                                    height=300)
        
        st.session_state.reformulated_prompt = edited_prompt
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back"):
                st.session_state.generation_step = 'initial'
                st.rerun()
        with col2:
            if st.button("Proceed with Generation ►"):
                st.session_state.generation_step = 'generating'
                st.rerun()
    
    # Generation step - actual application generation
    elif st.session_state.generation_step == 'generating':
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        output_path = st.session_state.output_path
        advanced_options = st.session_state.advanced_options
        
        app_generator = AppGenerator(api_key)
        
        status_text.text("Analyzing requirements...")
        progress_bar.progress(10)
        
        try:
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
            
            try:
                # Check if static website option is selected
                is_static = advanced_options.get('is_static_website', False)
                prompt_prefix = ""
                
                # If static website, add prefix to prompt to ensure proper detection
                if is_static:
                    prompt_prefix = "[STATIC WEBSITE] "
                    update_log("Preparing to generate static website (HTML/CSS/JavaScript only)")
                
                # Modify prompt if needed
                reformulated_prompt = st.session_state.reformulated_prompt
                if is_static and not reformulated_prompt.startswith("[STATIC WEBSITE]"):
                    reformulated_prompt = prompt_prefix + reformulated_prompt
                
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
                    
            except Exception as e:
                app_generator.generate_application.__globals__['print'] = original_print
                logger.exception("Application generation failed")
                raise e
            finally:
                app_generator.generate_application.__globals__['print'] = original_print
                
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("An error occurred during generation.")
            st.error(f"Error: {str(e)}")
            
            if st.button("Start Over"):
                st.session_state.generation_step = 'initial'
                st.rerun()
    
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