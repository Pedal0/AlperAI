import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main_app import AppGenerator
from dotenv import load_dotenv

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
            
            def print_override(message):
                nonlocal progress_value
                update_log(message)
                progress_value = min(progress_value + 5, 95)
                progress_bar.progress(progress_value)
            
            app_generator.generate_application.__globals__['print'] = print_override
            
            success = app_generator.generate_application(
                user_prompt, 
                output_path,
                include_tests=include_tests,
                create_docker=create_docker,
                add_ci_cd=add_ci_cd
            )
            
            if success:
                progress_bar.progress(100)
                st.balloons()
                status_text.text("Application generated successfully!")
                
                st.success(f"Your application has been generated at: {output_path}")
                
                st.subheader("Generated Files")
                files = []
                for root, dirs, filenames in os.walk(output_path):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
                
                for file in files:
                    rel_file = os.path.relpath(file, output_path)
                    with st.expander(rel_file):
                        with open(file, 'r') as f:
                            st.code(f.read(), language="python")
                
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