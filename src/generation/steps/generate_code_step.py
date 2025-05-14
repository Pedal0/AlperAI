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
Fonction d'étape : génération du code complet de l'application à partir du prompt et de la structure.
"""
import json
import re
import time
from pathlib import Path
from src.api.openrouter_api import call_openrouter_api
from src.utils.model_utils import is_free_model
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.mcp.tool_utils import get_default_tools

def generate_code_step(api_key, selected_model, reformulated_prompt, structure_lines, url_context, tool_results_text, url_reference, animation_instruction, use_mcp_tools, mcp_client, user_prompt, progress_callback=None, process_state=None):
    def update_progress(step, message, progress=None):
        if progress_callback:
            progress_callback(step, message, progress)

    # Vérifier la limite de taux pour les modèles gratuits
    if is_free_model(selected_model):
        current_time = time.time()
        last_api_call_time = process_state.get('last_api_call_time', 0) if process_state else 0
        time_since_last_call = current_time - last_api_call_time
        if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
            wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
            update_progress(4, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 70)
            time.sleep(wait_time)

    prompt_code_gen = f"""
    Generate the *complete* code for the application based on the prompt and structure below.
    **Detailed Prompt:**
    {reformulated_prompt}
    {tool_results_text if tool_results_text else ""}
    {url_reference if url_reference else ""}
    {url_context if url_context else ""}
    **Project Structure (for reference only):**
    ```
    {chr(10).join(structure_lines)}
    ```
    **Instructions:**
    1. Provide the full code for *all* files listed in the structure.
    2. Use the EXACT format `--- FILE: path/to/filename ---` on a line by itself before each file's code block. Start your response *immediately* with the first marker. No introduction text.
    3. Ensure the code is functional, includes necessary imports, basic error handling, and comments.
    4. For `requirements.txt` or similar, list the dependencies.
    5. For `README.md`, provide setup/run instructions.
    6. If the code exceeds token limits, end the *entire* response EXACTLY with: `GENERATION_INCOMPLETE` (no other text after).{animation_instruction}
    7. IMPORTANT: For web frameworks (e.g., Flask, Django, Express), ensure the application entrypoint configures its listening port via environment variable or CLI argument, never hardcoding port 5000.
    8. Generate two launch scripts at project root:
        - `start.sh` (for macOS/Linux) containing commands to install dependencies and start the application on macOS/Linux.
        - `start.bat` (for Windows) containing commands to install dependencies and start the application on Windows.
    IMPORTANT: If a style, template, or documentation is provided in the URLs, use them as the primary reference.
    Generate the code now:
    """

    # Load best system prompts for code generation as system message
    config_file = Path(__file__).parents[3] / 'config' / 'best_system_prompts.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            best_prompts_list = json.load(f)
        system_prompt_code = 'You are an AI code generator. Strictly adhere to these guidelines for output quality and format:\n' + ''.join(f'- {item}\n' for item in best_prompts_list)
    except Exception:
        system_prompt_code = 'You are an AI code generator. Follow best practices for clean, functional code.'

    # Prepare messages with system prompt
    messages_code_gen = [
        {"role": "system", "content": system_prompt_code},
        {"role": "user", "content": prompt_code_gen}
    ]

    if use_mcp_tools:
        response_code_gen = call_openrouter_api(
            api_key, 
            selected_model, 
            messages_code_gen, 
            temperature=0.4, 
            max_retries=2,
            tools=get_default_tools()
        )
    else:
        response_code_gen = call_openrouter_api(
            api_key, 
            selected_model, 
            messages_code_gen, 
            temperature=0.4, 
            max_retries=2
        )
    if process_state is not None:
        process_state['last_api_call_time'] = time.time()
    return response_code_gen
