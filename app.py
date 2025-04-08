import streamlit as st
from pathlib import Path
import time
import asyncio
import json

# Import from restructured modules
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.model_utils import is_free_model
from src.utils.env_utils import load_env_vars  # Add import for env variables loading
from src.api.openrouter_api import call_openrouter_api
from src.utils.file_utils import (
    parse_structure_and_prompt, 
    create_project_structure, 
    parse_and_write_code,
    identify_empty_files,
    generate_missing_code
)
from src.utils.prompt_utils import prompt_mentions_design
from src.ui.components import setup_page_config, render_sidebar, render_input_columns, show_response_expander

# Import MCP tools
from src.mcp.clients import SimpleMCPClient
from src.mcp.tool_utils import get_default_tools
from src.mcp.handlers import handle_tool_results

# Import frontend resources
from src.config.frontend_resources import (
    UI_LIBRARIES,
    COMPONENT_LIBRARIES,
    ANIMATION_RESOURCES,
    TEMPLATE_WEBSITES
)

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
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
if 'tool_results' not in st.session_state:
    st.session_state.tool_results = {}

# Render the UI components
api_key, selected_model = render_sidebar()
user_prompt, target_directory = render_input_columns()

# Add MCP Tools toggle in sidebar
with st.sidebar:
    st.subheader("🛠️ Advanced Options")
    use_mcp_tools = st.checkbox("Enable MCP Tools for enhanced generation", value=True, 
                                help="Use Model Context Protocol tools for web search, documentation lookup, and frontend components")
    
    if use_mcp_tools:
        st.subheader("🎨 Frontend Resources")
        frontend_framework = st.selectbox(
            "Preferred UI Framework",
            options=["Auto-detect", "Bootstrap", "Tailwind CSS", "Bulma", "Material Design"],
            index=0,
            help="Select a preferred frontend framework, or let the AI choose"
        )
        
        include_animations = st.checkbox(
            "Include Animations",
            value=True,
            help="Add CSS animations and transitions to make the UI more engaging"
        )

# Main generation button
generate_button = st.button("🚀 Generate Application", type="primary", disabled=st.session_state.process_running)

st.markdown("---") # Visual separator

# Utility function to handle async operations
async def run_mcp_query(client, query, context=None):
    result = await client.process_query(query, context)
    return result

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
        st.session_state.tool_results = {}
        
        # Initialize MCP client if tools are enabled
        if use_mcp_tools:
            st.session_state.mcp_client = SimpleMCPClient(api_key, selected_model)
            st.info("🔌 MCP Tools enabled: Web search, documentation lookup, and frontend components available.")

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

            # If MCP tools enabled, use them to enhance the prompt
            additional_context = ""
            if use_mcp_tools and st.session_state.mcp_client:
                status_placeholder_step1.info("🔍 Using MCP tools to analyze your request and gather information...")
                
                # Add frontend preferences to analysis query
                frontend_preferences = ""
                if frontend_framework != "Auto-detect":
                    frontend_preferences = f"For frontend, use {frontend_framework}. "
                if include_animations:
                    frontend_preferences += "Include CSS animations and transitions to make the UI engaging. "
                
                analysis_query = f"""
                Analyze this request for application development: "{user_prompt}"
                
                1. What kind of application is being requested?
                2. What frameworks or libraries might be needed?
                3. Do I need to search for any documentation to help with implementation?
                4. Would any frontend components be useful for this project?
                5. What kind of template would fit this application best?
                
                {frontend_preferences}
                
                Only use tools if necessary to clarify technical details or find specific components.
                """
                
                # Run the MCP query asynchronously
                mcp_result = asyncio.run(run_mcp_query(st.session_state.mcp_client, analysis_query))
                
                if mcp_result and "tool_calls" in mcp_result and mcp_result["tool_calls"]:
                    status_placeholder_step1.success("✅ Tools used to gather additional context for your project.")
                    
                    # Process and store tool results
                    for tool_call in mcp_result["tool_calls"]:
                        tool_name = tool_call.get("tool")
                        if tool_name:
                            st.session_state.tool_results[tool_name] = tool_call
                    
                    # Add this context to our prompt
                    additional_context = f"""
                    Additional context for generating this application:
                    {mcp_result.get('text', '')}
                    """
                
            # Building prompt for the first step
            prompt_step1 = f"""
            Analyze the user's request below. Your tasks are:
            1.  **Reformulate Request:** Create a detailed, precise prompt outlining features, technologies (assume standard web tech like Python/Flask or Node/Express if unspecified, or stick to HTML/CSS/JS if simple), and requirements. This will guide code generation. Include comments in generated code.
            2.  **Define Project Structure:** Propose a complete, logical file/directory structure. List each item on a new line. Use relative paths. Mark directories with a trailing '/'. DO NOT include comments (#) or backticks (```) in the structure list itself.

            User's Request:
            "{user_prompt}"
            
            {additional_context if additional_context else ""}

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
                        
                        # Add tool results if available
                        tool_results_text = ""
                        if use_mcp_tools and st.session_state.tool_results:
                            tool_results_text = "\n**Tool Results:** The following information was gathered to help with development:\n"
                            for tool_name, tool_info in st.session_state.tool_results.items():
                                st.write(f"**{tool_name}**")
                                st.write(f"Arguments: {tool_info.get('args', {})}")
                                if 'result' in tool_info:
                                    with st.expander(f"View {tool_name} results"):
                                        st.code(tool_info['result'])
                        
                        # Building prompt for code generation with MCP tool results
                        prompt_step2 = f"""
                        Generate the *complete* code for the application based on the prompt and structure below.

                        **Detailed Prompt:**
                        {st.session_state.reformulated_prompt}
                        
                        {tool_results_text if tool_results_text else ""}

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

                        # Use tools for code generation if enabled
                        if use_mcp_tools:
                            response_step2 = call_openrouter_api(
                                api_key, 
                                selected_model, 
                                messages_step2, 
                                temperature=0.4, 
                                max_retries=2,
                                tools=get_default_tools()
                            )
                        else:
                            # Use lower temperature for code generation for less creativity/errors
                            response_step2 = call_openrouter_api(
                                api_key, 
                                selected_model, 
                                messages_step2, 
                                temperature=0.4, 
                                max_retries=2
                            )
                        st.session_state.last_api_call_time = time.time()

                    if response_step2 and response_step2.get("choices"):
                        code_response_text = response_step2["choices"][0]["message"]["content"]
                        
                        # Check for tool calls
                        if use_mcp_tools and response_step2["choices"][0]["message"].get("tool_calls"):
                            status_placeholder_step3.info("🔍 AI is using tools to enhance code generation...")
                            
                            # Process each tool call
                            tool_calls = response_step2["choices"][0]["message"]["tool_calls"]
                            for tool_call in tool_calls:
                                function_info = tool_call.get("function", {})
                                tool_name = function_info.get("name")
                                tool_args_str = function_info.get("arguments", "{}")
                                
                                try:
                                    tool_args = json.loads(tool_args_str)
                                    
                                    # Execute the tool via MCP client
                                    tool_query = f"Execute {tool_name} with {tool_args}"
                                    tool_result = asyncio.run(run_mcp_query(st.session_state.mcp_client, tool_query))
                                    
                                    if tool_result:
                                        # Store the tool results
                                        st.session_state.tool_results[tool_name] = {
                                            "args": tool_args,
                                            "result": tool_result.get("text", "")
                                        }
                                        
                                        # Build a follow-up prompt with the tool results
                                        processed_result = handle_tool_results(tool_name, tool_result.get("text", ""))
                                        
                                        follow_up_prompt = f"""
                                        I've used {tool_name} to gather additional information for the code generation.
                                        
                                        The tool returned this information:
                                        
                                        {processed_result}
                                        
                                        Please use this additional information to improve the code generation.
                                        Continue generating the code using the same format:
                                        `--- FILE: path/to/filename ---`
                                        
                                        And remember to include all files from the structure.
                                        """
                                        
                                        # Make another API call with the follow-up prompt
                                        follow_up_messages = messages_step2 + [
                                            {"role": "assistant", "content": code_response_text},
                                            {"role": "user", "content": follow_up_prompt}
                                        ]
                                        
                                        status_placeholder_step3.info(f"🔍 Using information from {tool_name} to enhance code...")
                                        
                                        # Check rate limit
                                        if is_free_model(selected_model):
                                            current_time = time.time()
                                            time_since_last_call = time.time() - st.session_state.get('last_api_call_time', 0)
                                            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                                st.warning(f"⏳ Waiting {wait_time:.1f}s before continuing...")
                                                time.sleep(wait_time)
                                        
                                        # Make the follow-up call
                                        follow_up_response = call_openrouter_api(
                                            api_key, 
                                            selected_model, 
                                            follow_up_messages, 
                                            temperature=0.4
                                        )
                                        st.session_state.last_api_call_time = time.time()
                                        
                                        if follow_up_response and follow_up_response.get("choices"):
                                            # Update the code response with the enhanced version
                                            enhanced_code = follow_up_response["choices"][0]["message"]["content"]
                                            code_response_text = enhanced_code
                                except Exception as e:
                                    st.warning(f"Error processing tool {tool_name}: {e}")
                        
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

                            # == STEP 5: Check for Empty Files and Generate Missing Code ==
                            empty_files_check = st.checkbox("Check for empty files and generate their code", value=True)
                            
                            if empty_files_check and not errors and (files_written or generation_incomplete):
                                st.info("▶️ Step 5: Checking for empty files and generating missing code...")
                                status_placeholder_step5 = st.empty()
                                
                                with st.spinner("Identifying empty files..."):
                                    empty_files = identify_empty_files(target_directory, st.session_state.project_structure)
                                
                                if empty_files:
                                    status_placeholder_step5.warning(f"Found {len(empty_files)} empty files that need code generation.")
                                    st.write("Empty files:")
                                    for ef in empty_files:
                                        st.info(f"   📄 Empty file: {ef}")
                                    
                                    # Check rate limit before calling API again
                                    if is_free_model(selected_model):
                                        current_time = time.time()
                                        time_since_last_call = time.time() - st.session_state.get('last_api_call_time', 0)
                                        if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                            wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                            st.warning(f"⏳ Free model detected. Waiting {wait_time:.1f} seconds before generating missing code...")
                                            time.sleep(wait_time)
                                    
                                    with st.spinner("Generating code for empty files..."):
                                        additional_files, additional_errors = generate_missing_code(
                                            api_key, 
                                            selected_model, 
                                            empty_files, 
                                            st.session_state.reformulated_prompt, 
                                            st.session_state.project_structure,
                                            st.session_state.last_code_generation_response,
                                            target_directory
                                        )
                                        st.session_state.last_api_call_time = time.time()
                                    
                                    if additional_files:
                                        status_placeholder_step5.success(f"✅ Successfully generated code for {len(additional_files)} empty files.")
                                        st.subheader("Additional files filled:")
                                        for f in additional_files:
                                            st.success(f"   📄 File filled: {Path(f).relative_to(Path(target_directory))}")
                                        
                                        # Add to main file list
                                        files_written.extend(additional_files)
                                    
                                    if additional_errors:
                                        for err in additional_errors:
                                            st.error(f"   ❌ {err}")
                                        
                                        # Add to main error list
                                        errors.extend(additional_errors)
                                else:
                                    status_placeholder_step5.success("✅ No empty files found - all files contain code.")
                            
                            # Show tool results if any were used
                            if use_mcp_tools and st.session_state.tool_results:
                                with st.expander("View MCP Tool Results"):
                                    st.subheader("🔍 Tool Results Used")
                                    for tool_name, tool_info in st.session_state.tool_results.items():
                                        st.write(f"**{tool_name}**")
                                        st.write(f"Arguments: {tool_info.get('args', {})}")
                                        if 'result' in tool_info:
                                            with st.expander(f"View {tool_name} results"):
                                                st.code(tool_info['result'])
                            
                            # Final success message
                            if not errors:
                                st.success("🎉 Application generated successfully!")
                                st.balloons()
                            elif len(errors) < len(files_written) / 2:  # If errors are less than half the files
                                st.warning("🎯 Application generated with some errors. Check the error messages above.")
                            else:
                                st.error("❗️ Several errors occurred during application generation.")

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