"""
Fonction d'étape : définition de la structure du projet à partir du prompt reformulé.
"""
import re
import time
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

    prompt_structure = f"""
    Based on the reformulated prompt below, your task is to:
    1. Propose a complete and logical file/folder structure for this application.
    2. List each item on a new line. Use relative paths. Mark directories with a trailing '/'.
    3. Do NOT include comments (#) or backticks (```) in the structure list itself.
    4. If the user provided URLs, use any examples or structures found there as inspiration.
    5. Your output MUST be EXACTLY in the following format:
    ### STRUCTURE ###
    [List of files/folders, one per line, e.g.:
    src/
    src/main.py
    requirements.txt
    README.md]

    Reformulated prompt:
    {reformulated_prompt}
    {url_context if url_context else ""}
    """
    messages_structure = [{"role": "user", "content": prompt_structure}]
    response_structure = call_openrouter_api(api_key, selected_model, messages_structure, temperature=0.6, max_retries=2)
    if process_state is not None:
        process_state['last_api_call_time'] = time.time()
    update_progress(2, "Analyse de la réponse de structure...", 50)
    structure_lines = []
    if response_structure and response_structure.get("choices"):
        response_text = response_structure["choices"][0]["message"]["content"]
        structure_match = re.search(r"###\s*STRUCTURE\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if structure_match:
            structure_block = structure_match.group(1).strip()
            structure_block_cleaned = structure_block.strip().strip('`')
            potential_lines = structure_block_cleaned.split('\n')
            for line in potential_lines:
                line = line.strip()
                if not line or line == '```':
                    continue
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                if line:
                    structure_lines.append(line)
            if process_state is not None:
                process_state['project_structure'] = structure_lines
            update_progress(2, "✅ Structure du projet définie avec succès.", 55)
        else:
            update_progress(2, "⚠️ Format de réponse inattendu pour la structure.", 55)
            return None
    else:
        update_progress(2, "❌ Échec de la définition de la structure.", 55)
        return None
    return structure_lines
