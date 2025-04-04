import streamlit as st
from pathlib import Path
import time

# Import from restructured modules
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.model_utils import is_free_model
from src.utils.env_utils import load_env_vars  # Add import for env variables loading
from src.api.openrouter_api import call_openrouter_api
from src.utils.file_utils import parse_structure_and_prompt, create_project_structure, parse_and_write_code
from src.utils.prompt_utils import prompt_mentions_design
from src.ui.components import setup_page_config, render_sidebar, render_input_columns, show_response_expander

# Load environment variables at startup
load_env_vars()

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

# Main generation button
generate_button = st.button("🚀 Generate Application", type="primary", disabled=st.session_state.process_running)

st.markdown("---") # Visual separator

# --- Main Logic ---
if generate_button and not st.session_state.process_running:
    st.session_state.process_running = True # Prevent double-click
    valid_input = True
    if not api_key:
        st.error("Please enter your OpenRouter API key in the sidebar.")
        valid_input = False
    if not user_prompt:
        st.error("Please describe the application you want to generate.")
        valid_input = False
    if not target_directory:
        st.error("Please specify the destination folder path.")
        valid_input = False
    elif not Path(target_directory).is_dir(): # Check if the path is a valid folder
         st.error(f"The specified path '{target_directory}' is not a valid folder or does not exist.")
         valid_input = False

    if valid_input:
        st.session_state.last_code_generation_response = "" # Reset state
        st.session_state.reformulated_prompt = ""
        st.session_state.project_structure = []

        # == STEP 1: Reformulation and Structure ==
        st.info("▶️ Step 1: Prompt Reformulation and Structure Definition...")
        status_placeholder_step1 = st.empty() # To display status
        with st.spinner("Calling AI to reformulate and define structure..."):

            # Check rate limit for free models
            if is_free_model(selected_model):
                current_time = time.time()
                time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                    wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                    status_placeholder_step1.warning(f"⏳ Free model detected. Waiting {wait_time:.1f} seconds (rate limit)...")
                    time.sleep(wait_time)

            # Building prompt for the first step
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
            st.session_state.last_api_call_time = time.time() # Record time

        if response_step1 and response_step1.get("choices"):
            response_text_step1 = response_step1["choices"][0]["message"]["content"]
            reformulated_prompt, structure_lines = parse_structure_and_prompt(response_text_step1)

            if reformulated_prompt and structure_lines:
                st.session_state.reformulated_prompt = reformulated_prompt
                st.session_state.project_structure = structure_lines
                status_placeholder_step1.success("✅ Step 1 completed: Prompt reformulated and structure defined.")

                with st.expander("View Reformulated Prompt and Structure"):
                    st.subheader("Reformulated Prompt:")
                    st.markdown(f"```text\n{reformulated_prompt}\n```")
                    st.subheader("Proposed Project Structure (Cleaned):")
                    st.code("\n".join(structure_lines), language='text')

                # == STEP 2: Creating File/Folder Structure ==
                st.info("▶️ Step 2: Creating Physical Structure...")
                status_placeholder_step2 = st.empty()
                with st.spinner(f"Creating folders and files in '{target_directory}'..."):
                    created_paths = create_project_structure(target_directory, st.session_state.project_structure)

                if created_paths is not None:
                    status_placeholder_step2.success(f"✅ Step 2 completed: Structure created in '{target_directory}'.")

                    # == STEP 3: Code Generation ==
                    st.info("▶️ Step 3: Generating Complete Code...")
                    status_placeholder_step3 = st.empty()
                    with st.spinner("Calling AI to generate code (this may take time)..."):

                        # Check rate limit for free models
                        if is_free_model(selected_model):
                           current_time = time.time()
                           time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                           if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                               wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                               status_placeholder_step3.warning(f"⏳ Free model detected. Waiting {wait_time:.1f} seconds (rate limit)...")
                               time.sleep(wait_time)

                        # --- Adding animation instruction ---
                        animation_instruction = ""
                        if not prompt_mentions_design(user_prompt):
                             animation_instruction = (
                                 "\n7. **Animation & Fluidity:** Since no specific design was requested, "
                                 "please incorporate subtle CSS animations and transitions (e.g., hover effects, smooth section loading/transitions, subtle button feedback) "
                                 "to make the user interface feel modern, fluid, and engaging. Prioritize usability and avoid overly distracting animations."
                             )
                             st.info("ℹ️ No design instructions detected, adding request for fluid animations.")

                        # Building prompt for code generation
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

                        # Use lower temperature for code generation for less creativity/errors
                        response_step2 = call_openrouter_api(api_key, selected_model, messages_step2, temperature=0.4, max_retries=2)
                        st.session_state.last_api_call_time = time.time()

                    if response_step2 and response_step2.get("choices"):
                        code_response_text = response_step2["choices"][0]["message"]["content"]
                        st.session_state.last_code_generation_response = code_response_text # Store for display
                        status_placeholder_step3.success("✅ Step 3 completed: Code generation response received.")

                        # == STEP 4: Writing Code to Files ==
                        st.info("▶️ Step 4: Writing Code to Files...")
                        status_placeholder_step4 = st.empty()
                        files_written = []
                        errors = []
                        generation_incomplete = False
                        with st.spinner("Analyzing response and writing code..."):
                            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

                        if files_written or errors:
                            status_placeholder_step4.success(f"✅ Step 4 completed: Response processing finished.")
                            st.subheader("File writing results:")
                            for f in files_written:
                                st.success(f"   📄 File written: {Path(f).relative_to(Path(target_directory))}")
                            for err in errors:
                                st.error(f"   ❌ {err}")

                            if not errors and not generation_incomplete:
                                st.success("🎉 Application generated successfully!")
                                st.balloons()
                            elif generation_incomplete:
                                 st.warning("⚠️ Generation is incomplete. Generated code so far has been written. You may need to write the rest manually.")
                            elif errors:
                                st.error("❗️ Errors occurred while writing some files.")

                        else:
                             status_placeholder_step4.error("❌ Step 4 failed: No files could be written.")


                    else:
                        status_placeholder_step3.error("❌ Step 3 failed: Code generation retrieval failed.")
                        if response_step2: st.json(response_step2) # Display error response if available

                else: # Error during structure creation (handled in the function)
                   status_placeholder_step2.error("❌ Step 2 failed: Unable to create project structure.")

            else: # Error when parsing step 1
                status_placeholder_step1.error("❌ Step 1 failed: Unable to parse AI response (prompt/structure).")
                if 'response_text_step1' in locals():
                    with st.expander("View raw response from Step 1"):
                        st.code(response_text_step1, language='text')
        else: # Error during API call in step 1
             status_placeholder_step1.error("❌ Step 1 failed: API call for reformulation/structure failed.")
             if response_step1: st.json(response_step1) # Display error response if available

        st.session_state.process_running = False # Re-enable button
        st.info("🏁 Process completed.") # Indicate global end

    else: # Invalid input
        st.session_state.process_running = False # Re-enable button if input error

# Show response expander for debugging
show_response_expander()