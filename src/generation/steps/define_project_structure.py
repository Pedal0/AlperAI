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
Fonction d'étape : définition de la structure du projet à partir du prompt reformulé.
"""
import re
import time
import json
import logging
from src.api.openrouter_api import call_openrouter_api
from src.utils.model_utils import is_free_model
from src.config.constants import RATE_LIMIT_DELAY_SECONDS

def define_project_structure(api_key, selected_model, reformulated_prompt, url_context, progress_callback=None, process_state=None):
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
            update_progress(2, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 45)
            time.sleep(wait_time)

    # Nouveau : prompt pour output structuré JSON
    prompt_structure = f"""
    Based on the reformulated prompt below, your task is to:
    1. Propose a complete and logical file/folder structure for this application.
    2. Return ONLY a JSON object with a single key 'structure', whose value is a list of all files and folders (folders end with '/').
    3. Do NOT include comments, explanations, or code blocks. Output ONLY the JSON object.
    4. Example output:
    {{\n  \"structure\": [\n    \"src/\",\n    \"src/main.py\",\n    \"requirements.txt\",\n    \"README.md\"\n  ]\n}}
    5. If the user provided URLs, use any examples or structures found there as inspiration.
    Reformulated prompt:
    {reformulated_prompt}
    {url_context if url_context else ""}
    """
    messages_structure = [{"role": "user", "content": prompt_structure}]
    # Appel OpenRouter avec paramètre structured output
    response_structure = call_openrouter_api(
        api_key,
        selected_model,
        messages_structure,
        temperature=0.6,
        max_retries=2,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "project_structure",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "structure": {
                            "type": "array",
                            "description": "List of all files and folders (folders end with /)",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["structure"],
                    "additionalProperties": False
                }
            }
        }
    )
    logging.info(f"[DEBUG] Raw structure response: {response_structure}")
    if process_state is not None:
        process_state['last_api_call_time'] = time.time()
    update_progress(2, "Analyzing structure response...", 50)
    structure_lines = []
    # Nouveau : parsing JSON structuré
    if response_structure and response_structure.get("choices"):
        try:
            content = response_structure["choices"][0]["message"]["content"]
            if isinstance(content, str):
                json_obj = json.loads(content)
            else:
                json_obj = content
            structure_lines = json_obj.get("structure", [])
            if process_state is not None:
                process_state['project_structure'] = structure_lines
            update_progress(2, "✅ Project structure successfully parsed from JSON.", 55)
        except Exception as e:
            update_progress(2, f"⚠️ Failed to parse JSON structure: {e}", 55)
            return None
    else:
        update_progress(2, "❌ Failed to get structure from model.", 55)
        return None
    return structure_lines