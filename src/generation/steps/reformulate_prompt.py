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
Fonction d'étape : reformulation du prompt utilisateur pour la génération d'application.
"""
import re
import json
from pathlib import Path
from src.api.openrouter_api import call_openrouter_api
from src.utils.model_utils import is_free_model
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.prompt_loader import get_system_prompt_with_best_practices, get_agent_prompt
import time

def reformulate_prompt(api_key, selected_model, user_prompt, url_context, additional_context, progress_callback=None, current_app=None, process_state=None):
    """
    Reformule le prompt utilisateur pour guider la génération de code.
    Retourne le prompt reformulé ou None en cas d'échec.
    Met à jour process_state et current_app si fournis.
    """
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
            update_progress(1, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 20)
            time.sleep(wait_time)

    # Load system prompt with best practices using the new utility
    system_prompt = get_system_prompt_with_best_practices('prompt_reformulation_agent')

    # Load reformulation prompt template
    reformulation_template = get_agent_prompt(
        'prompt_reformulation_agent', 
        'reformulation_prompt',
        user_prompt=user_prompt,
        url_context=url_context if url_context else "",
        additional_context=additional_context if additional_context else ""
    )
    
    # Prepare messages with system prompt and user content
    messages_reformulation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": reformulation_template}
    ]
    response_reformulation = call_openrouter_api(api_key, selected_model, messages_reformulation, temperature=0.6, max_retries=2)
    if process_state is not None:
        process_state['last_api_call_time'] = time.time()
    update_progress(1, "Analyse de la réponse de reformulation...", 35)
    reformulated_prompt = None
    if response_reformulation and response_reformulation.get("choices"):
        response_text = response_reformulation["choices"][0]["message"]["content"]
        prompt_match = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if prompt_match:
            reformulated_prompt = prompt_match.group(1).strip()
            if process_state is not None:
                process_state['reformulated_prompt'] = reformulated_prompt
            if current_app:
                current_app.config['reformulated_prompt'] = reformulated_prompt
            update_progress(1, "✅ Prompt reformulé avec succès.", 40)
        else:
            update_progress(1, "⚠️ Format de réponse inattendu pour la reformulation.", 40)
            reformulated_prompt = response_text.strip()
            if process_state is not None:
                process_state['reformulated_prompt'] = reformulated_prompt
            if current_app:
                current_app.config['reformulated_prompt'] = reformulated_prompt
    else:
        update_progress(1, "❌ Échec de la reformulation du prompt.", 40)
        return None
    return reformulated_prompt