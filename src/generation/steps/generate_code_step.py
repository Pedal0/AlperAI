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
from src.utils.prompt_loader import get_system_prompt_with_best_practices, get_agent_prompt

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
            time.sleep(wait_time)    # Load system prompt with best practices using the new utility
    system_prompt_code = get_system_prompt_with_best_practices('code_generation_agent')

    # Load main generation prompt template
    prompt_code_gen = get_agent_prompt(
        'code_generation_agent',
        'main_generation_prompt',
        reformulated_prompt=reformulated_prompt,
        structure_lines=chr(10).join(structure_lines),
        url_context=url_context if url_context else "",
        tool_results_text=tool_results_text if tool_results_text else "",
        url_reference=url_reference if url_reference else "",
        animation_instruction=animation_instruction if animation_instruction else ""
    )

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