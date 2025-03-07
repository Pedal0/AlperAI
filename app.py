import streamlit as st
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main_app import AppGenerator
from src.app_validator import AppValidator
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

def main():
    load_dotenv()
    
    st.set_page_config(page_title="AI Application Generator", layout="wide")
    
    st.title("AI Application Generator")
    st.markdown("""
    This tool uses AI to generate complete applications based on your description.
    Just provide a detailed description of what you want to build, set the output directory,
    and click "Generate Application".
    """)
    
    api_key =  os.getenv("OPENAI_API_KEY", "")
    
    user_prompt = st.text_area("Describe the application you want to build", 
                              height=150,
                              placeholder="Example: Create a web application that allows users to manage their personal finances. It should track income, expenses, investments, and provide visualizations of spending patterns.")
    
    output_path = st.text_input("Output Directory", 
                               value=os.path.join(os.getcwd(), "generated_app"))
    
    with st.expander("Advanced Options"):
        include_tests = st.checkbox("Generate tests", value=False)
        create_docker = st.checkbox("Create Docker configuration", value=False)
        add_ci_cd = st.checkbox("Add CI/CD configuration", value=False)
    
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
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        
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
            
            # Store original print
            original_print = print
            app_generator.generate_application.__globals__['print'] = print_override
            
            try:
                success = app_generator.generate_application(
                    user_prompt, 
                    output_path,
                    include_tests=include_tests,
                    create_docker=create_docker,
                    add_ci_cd=add_ci_cd
                )
                
                if success:
                    status_text.text("Validating application...")
                    validator = AppValidator(app_generator.api_client)
                    validation_success = validator.validate_app(output_path, app_generator.project_context)
                    
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
                else:
                    status_text.text("Application generation failed.")
                    st.error("Failed to generate application. Please check the logs for details.")
                    
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

def create_zip(directory):
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

if __name__ == "__main__":
    main()