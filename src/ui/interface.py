import os
import streamlit as st
import time
import threading
import queue
import json
from src.config.constants import DEFAULT_OUTPUT_DIR, GENERATION_PHASES
from src.file_manager.project_generator import ProjectGenerator
from src.api.openrouter import optimize_prompt

# Queue for communicating between threads
generation_queue = queue.Queue()

def create_ui():
    """Create the main Streamlit user interface"""
    # Initialize session state variables if they don't exist
    if 'phase' not in st.session_state:
        st.session_state.phase = "input"  # Options: input, reformulation, generation, complete
    
    if 'progress' not in st.session_state:
        st.session_state.progress = 0.0
        
    if 'status' not in st.session_state:
        st.session_state.status = ""
        
    if 'optimized_prompt' not in st.session_state:
        st.session_state.optimized_prompt = ""
        
    if 'generation_result' not in st.session_state:
        st.session_state.generation_result = None

    if 'generation_running' not in st.session_state:
        st.session_state.generation_running = False
    
    # Check if there's a result in the queue
    if not generation_queue.empty():
        try:
            result = generation_queue.get_nowait()
            st.session_state.generation_result = result
            st.session_state.phase = "complete"
            st.session_state.generation_running = False
        except queue.Empty:
            pass
        
    # Render the appropriate phase
    if st.session_state.phase == "input":
        render_input_phase()
    elif st.session_state.phase == "reformulation":
        render_reformulation_phase()
    elif st.session_state.phase == "generation":
        render_generation_phase()
    elif st.session_state.phase == "complete":
        render_complete_phase()

def render_input_phase():
    """Render the initial input form"""
    st.write("### Describe Your Application")
    st.write("Enter a detailed description of the application you want to generate.")
    
    with st.form("input_form"):
        user_prompt = st.text_area(
            "Application Description",
            height=200,
            placeholder="Describe your application in detail. For example: 'A task management web application with user authentication, task creation, due dates, and completion tracking...'",
            help="Be as specific as possible about the features and functionality you want."
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            output_dir = st.text_input(
                "Output Directory", 
                DEFAULT_OUTPUT_DIR,
                help="Directory where the generated application will be saved"
            )
        
        with col2:
            # Add some advanced options
            generate_static = st.checkbox(
                "Generate Static Website", 
                value=False,
                help="Generate a static HTML/CSS/JS website without a backend server"
            )
            
            generate_tests = st.checkbox(
                "Generate Tests", 
                value=False,
                help="Include test files for the application"
            )
            
            generate_docker = st.checkbox(
                "Docker Configuration", 
                value=False,
                help="Add Dockerfile and docker-compose.yml files"
            )
            
            generate_ci = st.checkbox(
                "CI/CD Configuration", 
                value=False,
                help="Add GitHub Actions or similar CI/CD configuration"
            )
        
        submitted = st.form_submit_button("Generate Application")
        
        if submitted:
            if not user_prompt:
                st.error("Please enter an application description")
                return
                
            # Add advanced options to the prompt
            enhanced_prompt = user_prompt
            if generate_static:
                enhanced_prompt += "\nThis should be a static website using only HTML, CSS, and JavaScript."
                # Add more specific instructions for properly separating CSS and JS files
                enhanced_prompt += "\nIMPORTANT: All CSS styles must be in external CSS files, not in <style> tags in the HTML."
                enhanced_prompt += "\nIMPORTANT: All JavaScript code must be in external JS files, not in <script> tags in the HTML."
            if generate_tests:
                enhanced_prompt += "\nInclude comprehensive tests for all functionality."
            if generate_docker:
                enhanced_prompt += "\nInclude Docker configuration files for containerization."
            if generate_ci:
                enhanced_prompt += "\nInclude CI/CD configuration files for automated deployment."
            
            # Store the inputs in session state
            st.session_state.user_prompt = enhanced_prompt
            st.session_state.output_dir = output_dir
            
            # Move to reformulation phase
            with st.spinner("Analyzing your requirements..."):
                # Get the optimized prompt directly from the API function
                optimized_prompt = optimize_prompt(enhanced_prompt)
                
                # Create project generator and set the optimized prompt
                project_generator = ProjectGenerator(
                    enhanced_prompt, 
                    output_dir,
                    update_progress=None,
                    update_status=None
                )
                project_generator.optimized_prompt = optimized_prompt
                
                st.session_state.optimized_prompt = optimized_prompt
                st.session_state.phase = "reformulation"
                st.rerun()

def render_reformulation_phase():
    """Render the prompt reformulation review"""
    st.write("### Review Refined Requirements")
    st.write("I've analyzed and refined your requirements. Please review them and make any necessary adjustments.")
    
    optimized_prompt = st.text_area(
        "Refined Requirements",
        value=st.session_state.optimized_prompt,
        height=300
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back"):
            st.session_state.phase = "input"
            st.rerun()
            
    with col2:
        if st.button("Proceed with Generation →"):
            st.session_state.optimized_prompt = optimized_prompt
            st.session_state.phase = "generation"
            st.rerun()

class ProgressUpdater:
    def __init__(self):
        self.progress = 0.0
        self.status = ""

    def update_progress(self, progress):
        self.progress = progress
        
    def update_status(self, status):
        self.status = status
        
    def apply_to_session_state(self):
        st.session_state.progress = self.progress
        st.session_state.status = self.status

progress_updater = ProgressUpdater()

def update_progress(progress):
    """Update the progress bar"""
    progress_updater.update_progress(progress)
    
def update_status(status):
    """Update the status message"""
    progress_updater.update_status(status)
    
def start_generation_thread(optimized_prompt, output_dir):
    """Start the generation process in a separate thread"""
    try:
        project_generator = ProjectGenerator(
            optimized_prompt,
            output_dir,
            update_progress=update_progress,
            update_status=update_status
        )
        
        result = project_generator.generate()
        # Put the result in the queue instead of modifying session state directly
        generation_queue.put(result)
    except Exception as e:
        print(f"Error in generation thread: {str(e)}")
        generation_queue.put({'error': True, 'message': str(e)})
    
def render_generation_phase():
    """Render the generation progress"""
    st.write("### Generating Your Application")
    st.write("Please wait while I generate your application. This may take a few minutes.")
    
    # Apply any updates from the progress updater to session state
    progress_updater.apply_to_session_state()
    
    # Display progress bar
    progress_bar = st.progress(st.session_state.progress)
    
    # Display status
    status_container = st.empty()
    status_container.info(st.session_state.status or "Preparing to generate application...")
    
    # Display progress phases
    phase_container = st.empty()
    phases_html = ""
    for i, phase in enumerate(GENERATION_PHASES):
        status_class = "complete" if st.session_state.progress * len(GENERATION_PHASES) > i else "pending"
        phases_html += f'<div class="phase-item {status_class}">{i+1}. {phase}</div>'
    
    phase_container.markdown(f'<div class="phase-container">{phases_html}</div>', unsafe_allow_html=True)
    
    # Auto refresh UI every 2 seconds to show progress updates
    if "refresh_counter" not in st.session_state:
        st.session_state.refresh_counter = 0
    
    st.session_state.refresh_counter += 1
    st.empty().markdown(f'<div style="display:none">{st.session_state.refresh_counter}</div>', unsafe_allow_html=True)
    
    # Start generation if not already running
    if not st.session_state.generation_running:
        st.session_state.generation_running = True
        # Start generation in a separate thread with explicit parameters instead of accessing session_state
        optimized_prompt = st.session_state.optimized_prompt
        output_dir = st.session_state.output_dir
        generation_thread = threading.Thread(
            target=start_generation_thread, 
            args=(optimized_prompt, output_dir)
        )
        generation_thread.daemon = True
        generation_thread.start()
    
    # Rerun every 2 seconds to check for updates from the thread
    time.sleep(2)
    st.rerun()

def render_complete_phase():
    """Render the completion page with download links"""
    st.write("### Application Generated Successfully! 🎉")
    
    result = st.session_state.generation_result
    
    if not result:
        st.error("An error occurred during generation. Please try again.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.rerun()
        return
    
    # Check if we have an error message
    if result.get('error'):
        st.error(f"Error: {result.get('message', 'Unknown error')}")
        if st.button("Start Over"):
            st.session_state.clear()
            st.rerun()
        return
    
    # Make sure app_name exists, use a fallback if not
    app_name = result.get('app_name', 'generated_application')
    st.write(f"Your application **{app_name}** has been generated successfully.")
    
    # Display download link for the ZIP file
    if os.path.exists(result['zip_path']):
        with open(result['zip_path'], "rb") as f:
            st.download_button(
                label="Download Application (ZIP)",
                data=f,
                file_name=f"{app_name}.zip",
                mime="application/zip",
                help="Download the complete application as a ZIP file"
            )
    else:
        st.warning(f"ZIP file not found at {result['zip_path']}. Please check the generated files directly at {result['output_dir']}")
    
    # Display app details
    st.write("### Application Details")
    st.write(f"**Output Directory:** `{result['output_dir']}`")
    st.write(f"**ZIP File:** `{result['zip_path']}`")
    
    # Display element dictionary if available
    if result.get('element_dictionary'):
        with st.expander("View Element Dictionary"):
            try:
                element_dict = json.loads(result['element_dictionary'])
                st.json(element_dict)
            except:
                st.code(result['element_dictionary'])
    
    # Display the optimized prompt
    with st.expander("View Application Requirements"):
        st.write(result.get('optimized_prompt', 'No requirements information available'))
    
    # Option to start over
    if st.button("Create Another Application"):
        st.session_state.clear()
        st.rerun()
