"""
Fonction d'étape : génération du code complet de l'application à partir du prompt et de la structure.
"""
import json
import re
import time
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
    Générez le code *complet* de l'application basé sur le prompt et la structure ci-dessous.
    **Prompt Détaillé:**
    {reformulated_prompt}
    {tool_results_text if tool_results_text else ""}
    {url_reference if url_reference else ""}
    {url_context if url_context else ""}
    **Structure du Projet (uniquement pour référence):**
    ```
    {chr(10).join(structure_lines)}
    ```
    **Instructions:**
    1. Fournissez le code complet pour *tous* les fichiers listés dans la structure.
    2. Utilisez le format EXACT `--- FILE: chemin/vers/nomfichier ---` sur une ligne par lui-même avant chaque bloc de code de fichier. Commencez la réponse *immédiatement* avec le premier marqueur. Aucun texte d'introduction.
    3. Assurez-vous que le code est fonctionnel, inclut les imports, la gestion des erreurs de base et des commentaires.
    4. Pour `requirements.txt` ou similaire, listez les dépendances.
    5. Pour `README.md`, fournissez des instructions de configuration/exécution.
    6. Si le code dépasse les limites de jetons, terminez la réponse *entière* *exactement* avec: `GENERATION_INCOMPLETE` (aucun autre texte après).{animation_instruction}
    IMPORTANT: SI un style, template ou documentation est fourni dans les URLs, utilisez-les comme référence primaire.
    Générez le code maintenant:
    """
    messages_code_gen = [{"role": "user", "content": prompt_code_gen}]
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
