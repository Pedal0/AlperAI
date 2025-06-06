# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

"""
Module for managing the application generation process.
Contains the steps and logic for generating applications.
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
from src.generation.steps.check_and_enhance_readme import check_and_enhance_readme
from src.generation.steps.analyze_user_needs import analyze_user_needs

def generate_application(api_key, selected_model, user_prompt, target_directory, use_mcp_tools=True, frontend_framework="Auto-detect", include_animations=True, progress_callback=None):
    """
    Generate a complete application based on the user's description.
    
    Args:
        api_key (str): OpenRouter API key
        selected_model (str): Selected AI model
        user_prompt (str): Application description
        target_directory (str): Destination directory
        use_mcp_tools (bool, optional): Use MCP tools to improve generation
        frontend_framework (str, optional): Preferred frontend framework
        include_animations (bool, optional): Include CSS animations
        progress_callback (function, optional): Progress update callback
        
    Returns:
        bool: True if generation succeeded, False otherwise
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
        update_progress(0, "🔌 MCP tools enabled: Web search, documentation, and frontend components available.", 4, progress_callback)

        import asyncio
        from src.generation.steps.run_mcp_query import run_mcp_query
        web_query = f"Find the most relevant and up-to-date information, best practices, and documentation for building this type of project: {user_prompt}"
        web_result = asyncio.run(run_mcp_query(mcp_client, web_query))
        if web_result and web_result.get("text"):
            mcp_context += "\n# Web Search Results\n" + web_result["text"]
            update_progress(0, "Web search results integrated into context.", 5, progress_callback)

        if frontend_framework and frontend_framework.lower() not in ["auto-detect", "none", ""]:
            doc_query = f"Find the official documentation and best practices for using the frontend framework: {frontend_framework}"
            doc_result = asyncio.run(run_mcp_query(mcp_client, doc_query))
            if doc_result and doc_result.get("text"):
                mcp_context += f"\n# Documentation for {frontend_framework}\n" + doc_result["text"]
                update_progress(0, f"Documentation for {frontend_framework} integrated into context.", 7, progress_callback)

    # == STEP 0: Extract and process URLs from prompt ==
    update_progress(0, "Extracting URLs from prompt...", 8, progress_callback)
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
            
            update_progress(0, f"✅ Content retrieved for {len(url_contents)} URL(s)", 12, progress_callback)
        except Exception as e:
            update_progress(0, f"❌ Error while retrieving URLs: {e}", 12, progress_callback)
            # Continue even if error

    # Ajoute le contexte MCP à la reformulation du prompt si présent
    if mcp_context:
        if 'reformulated_prompt' in process_state:
            process_state['reformulated_prompt'] += "\n" + mcp_context
        else:
            process_state['reformulated_prompt'] = mcp_context

    # == STEP 1: Reformulate prompt ==
    update_progress(1, "Reformulating prompt...", 15, progress_callback)
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

    # == NOUVELLE ÉTAPE : Analyse des besoins utilisateur ==
    update_progress(1, "Analyzing user needs to determine required steps...", 18, progress_callback)
    steps_to_run = analyze_user_needs(user_prompt)
    process_state['steps_to_run'] = steps_to_run
    logging.info(f"[GENERATION] Steps to run: {steps_to_run}")

    # == STEP 2: Define project structure ==
    update_progress(2, "Defining project structure...", 25, progress_callback)
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
    update_progress(3, f"Creating folders and files in '{target_directory}'...", 35, progress_callback)
    created_paths = create_project_structure(target_directory, structure_lines)

    if created_paths is not None:
        update_progress(3, f"✅ Structure created in '{target_directory}'.", 40, progress_callback)

        # == STEP 4: Code generation ==
        steps_to_run = process_state.get('steps_to_run', [])
        if not steps_to_run:
            update_progress(4, "❌ No generation steps detected. Aborting.", 100, progress_callback)
            return False

        # Génération par bloc selon les étapes demandées
        code_responses = {}
        from src.generation.steps.generate_frontend_step import generate_frontend_step
        from src.generation.steps.generate_backend_step import generate_backend_step
        from src.generation.steps.generate_tests_step import generate_tests_step
        from src.generation.steps.generate_documentation_step import generate_documentation_step
        
        if "frontend" in steps_to_run:
            update_progress(4, "Generating frontend...", 45, progress_callback)
            code_responses["frontend"] = generate_frontend_step(
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
        
        if "backend" in steps_to_run:
            update_progress(4, "Generating backend...", 50, progress_callback)
            code_responses["backend"] = generate_backend_step(
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
        if "tests" in steps_to_run:
            update_progress(4, "Generating tests...", 53, progress_callback)
            code_responses["tests"] = generate_tests_step(
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
        if "documentation" in steps_to_run or "readme" in steps_to_run:
            update_progress(4, "Generating documentation...", 55, progress_callback)
            code_responses["documentation"] = generate_documentation_step(
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
        # Fusionner les réponses pour la suite du flow (écriture des fichiers, etc.)
        # Pour l'instant, on ne traite que le frontend comme code principal si présent, sinon backend, sinon tests, sinon doc
        main_code_response = code_responses.get("frontend") or code_responses.get("backend") or code_responses.get("tests") or code_responses.get("documentation")
        response_code_gen = main_code_response
        process_state['last_api_call_time'] = time.time()

        if response_code_gen and response_code_gen.get("choices"):
            code_response_text = response_code_gen["choices"][0]["message"]["content"]
            
            # Tool calls
            if use_mcp_tools and response_code_gen["choices"][0]["message"].get("tool_calls") and mcp_client:
                update_progress(4, "🔍 AI is using tools to improve code generation...", 60, progress_callback)
                
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
            update_progress(4, "✅ Code generation response received.", 65, progress_callback)            # == STEP 5: Write code to files ==
            update_progress(5, "Writing code to files...", 70, progress_callback)
            files_written = []
            errors = []
            generation_incomplete = False
            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

            # == ÉTAPE CRITIQUE: Nettoyage universel des marqueurs Markdown ==
            if files_written:
                update_progress(5, "🧹 Cleaning markdown artifacts from generated files...", 72, progress_callback)
                from src.mcp.simple_validation_system import clean_markdown_artifacts
                
                cleanup_count = clean_markdown_artifacts(target_directory)
                if cleanup_count > 0:
                    update_progress(5, f"✅ Cleaned {cleanup_count} files of markdown artifacts.", 74, progress_callback)
                    logging.info(f"🧹 Cleaned markdown artifacts from {cleanup_count} files")
                else:
                    update_progress(5, "✅ No markdown artifacts found to clean.", 74, progress_callback)

            if files_written or errors:
                update_progress(5, "✅ Response processing complete.", 76, progress_callback)
                
                # Log results
                for f in files_written:
                    logging.info(f"📄 File written: {Path(f).relative_to(Path(target_directory))}")
                for err in errors:
                    logging.error(f"❌ {err}")                # == STEP 6: Check empty files and generate missing code ==
                if not errors and (files_written or generation_incomplete):
                    update_progress(6, "Checking for empty files...", 78, progress_callback)
                    
                    empty_files = identify_empty_files(target_directory, structure_lines)
                    
                    if empty_files:
                        update_progress(6, f"Found {len(empty_files)} empty files that need code generation.", 79, progress_callback)
                        
                        # Check rate limit before calling the API again
                        if is_free_model(selected_model):
                            current_time = time.time()
                            time_since_last_call = time.time() - process_state.get('last_api_call_time', 0)
                            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                update_progress(6, f"⏳ Free model detected. Waiting {wait_time:.1f} seconds before generating missing code...", 81, progress_callback)
                                time.sleep(wait_time)
                        
                        update_progress(6, "Generating code for empty files...", 83, progress_callback)
                        additional_files, additional_errors = generate_missing_code(
                            api_key, 
                            selected_model, 
                            empty_files, 
                            reformulated_prompt, 
                            structure_lines,
                            code_response_text,
                            target_directory                        )
                        process_state['last_api_call_time'] = time.time()
                        if additional_files:
                            update_progress(6, f"✅ Successfully generated code for {len(additional_files)} empty files.", 86, progress_callback)
                            # Add to main file list
                            files_written.extend(additional_files)
                            # Nettoyage des nouveaux fichiers générés
                            update_progress(6, "🧹 Cleaning new files...", 87, progress_callback)
                            from src.mcp.simple_validation_system import clean_markdown_artifacts
                            additional_cleanup = clean_markdown_artifacts(target_directory)
                            if additional_cleanup > 0:
                                logging.info(f"🧹 Cleaned {additional_cleanup} additional files")
                        
                        if additional_errors:
                            for err in additional_errors:
                                logging.error(f"❌ {err}")
                            # Add to main error list
                            errors.extend(additional_errors)
                    else:
                        update_progress(6, "✅ No empty files found - all files contain code.", 86, progress_callback)                  # Final success message
                if not errors:
                    update_progress(7, "🎉 Application generated successfully!", 91, progress_callback)                    # == STEP 8: Generate launch scripts ==
                    update_progress(8, "🛠️ Generating launch instructions based on README.md...", 93, progress_callback)
                    try:
                        from src.preview.handler.generate_start_scripts import generate_start_scripts
                        generate_start_scripts(target_directory, api_key, selected_model)
                        update_progress(8, "✅ Launch instructions created based on README.md.", 94, progress_callback)
                        try:
                            from src.preview.steps.improve_readme import improve_readme_for_preview
                            if improve_readme_for_preview(target_directory):
                                update_progress(8, "✅ README.md has been enhanced with detailed instructions.", 95, progress_callback)
                        except Exception as e:
                            logging.error(f"Failed to enhance README: {e}")
                    except Exception as e:
                        logging.error(f"Failed to generate launch instructions: {e}")
                        update_progress(8, "⚠️ Failed to generate launch instructions.", 95, progress_callback)                    # == STEP 9: Simple RepoMix-based validation and auto-correction ==
                    from src.mcp.simple_validation_system import validate_and_fix_with_repomix
                    repomix_validation_enabled = True  # Simple et fiable
                    if repomix_validation_enabled:
                        update_progress(9, "🔍 RepoMix codebase analysis and validation...", 95, progress_callback)
                        # Use reformulated prompt for better validation context
                        reformulated_for_validation = process_state.get('reformulated_prompt', reformulated_prompt)
                        valid, validation_message = validate_and_fix_with_repomix(
                            target_directory,
                            api_key=api_key,
                            model=selected_model,
                            user_prompt=user_prompt,
                            reformulated_prompt=reformulated_for_validation,
                            progress_callback=progress_callback
                        )
                        if valid:
                            update_progress(10, f"✅ RepoMix validation: {validation_message}", 100, progress_callback)
                        else:
                            update_progress(10, f"⚠️ RepoMix validation failed: {validation_message}", 100, progress_callback)
                    
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