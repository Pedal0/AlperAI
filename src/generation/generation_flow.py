"""
Module de gestion du processus de génération d'applications.
Contient les étapes et la logique de génération d'applications.
"""
import time
import asyncio
import json
import logging
import re
from pathlib import Path
from flask import session

from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.model_utils import is_free_model
from src.api.openrouter_api import call_openrouter_api
from src.utils.file_utils import (
    parse_structure_and_prompt, 
    create_project_structure,
    parse_and_write_code,
    identify_empty_files,
    generate_missing_code
)
from src.utils.prompt_utils import (
    prompt_mentions_design,
    extract_urls_from_prompt,
    process_urls
)
from src.mcp.tool_utils import get_default_tools
from src.mcp.handlers import handle_tool_results
from src.generation.steps.reformulate_prompt import reformulate_prompt
from src.generation.steps.define_project_structure import define_project_structure
from src.generation.steps.generate_code_step import generate_code_step
from src.generation.steps.add_used_tool import add_used_tool
from src.generation.steps.update_progress import update_progress
from src.generation.steps.run_mcp_query import run_mcp_query

def generate_application(api_key, selected_model, user_prompt, target_directory, use_mcp_tools=True, frontend_framework="Auto-detect", include_animations=True, progress_callback=None):
    """
    Génère une application complète basée sur la description de l'utilisateur.
    
    Args:
        api_key (str): Clé API OpenRouter
        selected_model (str): Modèle d'IA sélectionné
        user_prompt (str): Description de l'application souhaitée
        target_directory (str): Répertoire de destination
        use_mcp_tools (bool, optional): Utiliser les outils MCP pour améliorer la génération
        frontend_framework (str, optional): Framework frontend préféré
        include_animations (bool, optional): Inclure des animations CSS
        progress_callback (function, optional): Fonction pour mettre à jour la progression
        
    Returns:
        bool: True si la génération a réussi, False sinon
    """
    from flask import current_app

    # Variables locales au lieu d'utiliser la session Flask
    process_state = {
        'process_running': True,
        'last_code_generation_response': "",
        'reformulated_prompt': "",
        'project_structure': [],
        'tool_results': {},
        'url_contents': {},
        'last_api_call_time': 0,
        'used_tools_details': []  # Initialiser la liste pour suivre les outils utilisés
    }

    # Initialiser le client MCP si les outils sont activés
    mcp_client = None
    mcp_context = ""
    if use_mcp_tools:
        update_progress(0, "Using MCP tools to gather context and documentation...", 2, progress_callback)
        from src.mcp.clients import SimpleMCPClient
        mcp_client = SimpleMCPClient(api_key, selected_model)
        update_progress(0, "🔌 MCP tools enabled: Web search, documentation, and frontend components available.", progress_callback)

        import asyncio
        from src.generation.steps.run_mcp_query import run_mcp_query
        web_query = f"Find the most relevant and up-to-date information, best practices, and documentation for building this type of project: {user_prompt}"
        web_result = asyncio.run(run_mcp_query(mcp_client, web_query))
        if web_result and web_result.get("text"):
            mcp_context += "\n# Web Search Results\n" + web_result["text"]
            update_progress(0, "Web search results integrated into context.", progress_callback)

        if frontend_framework and frontend_framework.lower() not in ["auto-detect", "none", ""]:
            doc_query = f"Find the official documentation and best practices for using the frontend framework: {frontend_framework}"
            doc_result = asyncio.run(run_mcp_query(mcp_client, doc_query))
            if doc_result and doc_result.get("text"):
                mcp_context += f"\n# Documentation for {frontend_framework}\n" + doc_result["text"]
                update_progress(0, f"Documentation for {frontend_framework} integrated into context.", progress_callback)

    # == STEP 0: Extract and process URLs from prompt ==
    update_progress(0, "Extracting URLs from prompt...", 5, progress_callback)
    urls = extract_urls_from_prompt(user_prompt)
    url_context = ""
    
    if urls:
        update_progress(0, f"🔗 URLs detected in your request: {len(urls)} URL(s)", 10, progress_callback)
        try:
            url_contents = asyncio.run(process_urls(urls))
            process_state['url_contents'] = url_contents
            
            # Prepare context from URLs
            url_context = "\n\n### CONTENT OF PROVIDED URLS ###\n"
            for url, content in url_contents.items():
                truncated_content = content[:5000] + "..." if len(content) > 5000 else content
                url_context += f"\nURL: {url}\n```\n{truncated_content}\n```\n"
            
            update_progress(0, f"✅ Content retrieved for {len(url_contents)} URL(s)", 15, progress_callback)
        except Exception as e:
            update_progress(0, f"❌ Error while retrieving URLs: {e}", 15, progress_callback)
            # Continue even if error

    # Ajoute le contexte MCP à la reformulation du prompt si présent
    if mcp_context:
        if 'reformulated_prompt' in process_state:
            process_state['reformulated_prompt'] += "\n" + mcp_context
        else:
            process_state['reformulated_prompt'] = mcp_context

    # == STEP 1: Reformulate prompt ==
    update_progress(1, "Reformulating prompt...", 20, progress_callback)
    additional_context = ""
    tool_results_text = ""
    url_reference = ""
    animation_instruction = ""
    reformulated_prompt = reformulate_prompt(
        api_key,
        selected_model,
        user_prompt,
        url_context,
        additional_context,
        progress_callback=progress_callback,
        current_app=current_app,
        process_state=process_state
    )
    if not reformulated_prompt:
        update_progress(1, "❌ Failed to reformulate prompt.", 40, progress_callback)
        return False

    # == STEP 2: Define project structure ==
    update_progress(2, "Defining project structure...", 45, progress_callback)
    structure_lines = define_project_structure(
        api_key,
        selected_model,
        reformulated_prompt,
        url_context,
        progress_callback=progress_callback,
        process_state=process_state
    )
    if not structure_lines:
        return False

    # == STEP 3: Create file/folder structure ==
    update_progress(3, f"Creating folders and files in '{target_directory}'...", 60, progress_callback)
    created_paths = create_project_structure(target_directory, structure_lines)

    if created_paths is not None:
        update_progress(3, f"✅ Structure created in '{target_directory}'.", 65, progress_callback)

        # == STEP 4: Code generation ==
        if include_animations and not prompt_mentions_design(user_prompt):
            animation_instruction = (
                "\n7. **Animation & Fluidity:** Since no specific design was requested, "
                "please incorporate subtle CSS animations and transitions (e.g., hover effects, smooth section transitions, subtle button feedback) "
                "to make the UI modern, smooth, and attractive. Prioritize usability and avoid overly distracting animations."
            )
            update_progress(4, "ℹ️ No design instructions detected, adding a request for smooth animations.", 75, progress_callback)
        if use_mcp_tools and process_state.get('tool_results'):
            tool_results_text = "\n**Tool Results:** The following information was gathered to assist development:\n"
            for tool_name, tool_info in process_state['tool_results'].items():
                tool_results_text += f"\n- **{tool_name}**: {json.dumps(tool_info.get('args', {}))}\n"
                if 'result' in tool_info:
                    tool_results_text += f"Result: {tool_info['result'][:500]}...\n"
        if process_state.get('url_contents'):
            url_reference = "\n**Provided URLs:** Please refer to the URLs provided by the user as inspiration or documentation. Follow examples or documentation from these URLs as much as possible."
        update_progress(4, "Generating full code...", 70, progress_callback)
        response_code_gen = generate_code_step(
            api_key,
            selected_model,
            reformulated_prompt,
            structure_lines,
            url_context,
            tool_results_text,
            url_reference,
            animation_instruction,
            use_mcp_tools,
            mcp_client,
            user_prompt,
            progress_callback=progress_callback,
            process_state=process_state
        )
        process_state['last_api_call_time'] = time.time()

        if response_code_gen and response_code_gen.get("choices"):
            code_response_text = response_code_gen["choices"][0]["message"]["content"]
            
            # Tool calls
            if use_mcp_tools and response_code_gen["choices"][0]["message"].get("tool_calls") and mcp_client:
                update_progress(4, "🔍 AI is using tools to improve code generation...", 80, progress_callback)
                
                tool_calls = response_code_gen["choices"][0]["message"]["tool_calls"]
                for tool_call in tool_calls:
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    tool_args_str = function_info.get("arguments", "{}")

                    if not tool_name: continue  # Ignore if tool name is missing

                    try:
                        tool_args = json.loads(tool_args_str)

                        # Execute the tool via the MCP client
                        tool_query = f"Execute {tool_name} with {tool_args}"
                        tool_result = asyncio.run(run_mcp_query(mcp_client, tool_query))

                        if tool_result:
                            tool_result_text = tool_result.get("text", "")
                            extracted_details = None

                            # Extract URLs if it's Web Search
                            if tool_name == 'Web Search':
                                # Simple regex to find URLs
                                urls_found = re.findall(r'https?://[^\s"\']+', tool_result_text)
                                extracted_details = list(set(urls_found))  # Unique list of URLs

                            # Record the tool and its details (URLs for Web Search)
                            add_used_tool(process_state, tool_name, extracted_details)

                            # Store raw results (may be useful for debugging)
                            if 'tool_results' not in process_state:
                                process_state['tool_results'] = {}
                            process_state['tool_results'][tool_name] = {
                                "args": tool_args,
                                "result": tool_result_text  # Store raw result text
                            }

                            # Build a follow-up prompt with tool results
                            processed_result = handle_tool_results(tool_name, tool_result_text)
                            # ... (rest of tool result processing and follow-up call) ...

                    except Exception as e:
                        logging.warning(f"Error processing tool {tool_name}: {e}")
                        add_used_tool(process_state, tool_name, {'error': str(e)})  # Record the tool even in case of error

            process_state['last_code_generation_response'] = code_response_text
            update_progress(4, "✅ Code generation response received.", 90, progress_callback)

            # == STEP 5: Write code to files ==
            update_progress(5, "Writing code to files...", 90, progress_callback)
            files_written = []
            errors = []
            generation_incomplete = False
            
            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

            if files_written or errors:
                update_progress(5, "✅ Response processing complete.", 95, progress_callback)
                
                # Log results
                for f in files_written:
                    logging.info(f"📄 File written: {Path(f).relative_to(Path(target_directory))}")
                for err in errors:
                    logging.error(f"❌ {err}")

                # == STEP 6: Check empty files and generate missing code ==
                if not errors and (files_written or generation_incomplete):
                    update_progress(6, "Checking for empty files...", 95, progress_callback)
                    
                    empty_files = identify_empty_files(target_directory, structure_lines)
                    
                    if empty_files:
                        update_progress(6, f"Found {len(empty_files)} empty files that need code generation.", 95, progress_callback)
                        
                        # Check rate limit before calling the API again
                        if is_free_model(selected_model):
                            current_time = time.time()
                            time_since_last_call = time.time() - process_state.get('last_api_call_time', 0)
                            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                update_progress(6, f"⏳ Free model detected. Waiting {wait_time:.1f} seconds before generating missing code...", 95, progress_callback)
                                time.sleep(wait_time)
                        
                        update_progress(6, "Generating code for empty files...", 97, progress_callback)
                        additional_files, additional_errors = generate_missing_code(
                            api_key, 
                            selected_model, 
                            empty_files, 
                            reformulated_prompt, 
                            structure_lines,
                            code_response_text,
                            target_directory
                        )
                        process_state['last_api_call_time'] = time.time()
                        
                        if additional_files:
                            update_progress(6, f"✅ Successfully generated code for {len(additional_files)} empty files.", 98, progress_callback)
                            # Add to main file list
                            files_written.extend(additional_files)
                        
                        if additional_errors:
                            for err in additional_errors:
                                logging.error(f"❌ {err}")
                            # Add to main error list
                            errors.extend(additional_errors)
                    else:
                        update_progress(6, "✅ No empty files found - all files contain code.", 98, progress_callback)
                
                # Final success message
                if not errors:
                    update_progress(7, "🎉 Application generated successfully!", 100, progress_callback)
                    
                    # Save path for preview mode if in Flask context
                    if current_app:
                        current_app.config['last_generated_app_path'] = target_directory
                        current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                    
                    return True
                else:
                    update_progress(7, f"⚠️ Application generated with {len(errors)} errors.", 100, progress_callback)
                    if current_app:
                        current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                    return len(files_written) > 0
            else:
                update_progress(5, "❌ Failed to write files.", 100, progress_callback)
                if current_app:
                    current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                return False
        else:
            update_progress(4, "❌ Code generation failed.", 100, progress_callback)
            if current_app:
                current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
            return False
    else:
        update_progress(3, "❌ Failed to create structure.", 100, progress_callback)
        if current_app:
            current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
        return False


