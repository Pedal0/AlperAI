"""
Module de gestion du processus de génération d'applications.
Contient les étapes et la logique de génération d'applications.
"""
import time
import asyncio
import json
import logging
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

async def run_mcp_query(client, query, context=None):
    """
    Exécute une requête MCP de manière asynchrone.
    
    Args:
        client: Client MCP
        query (str): Requête à exécuter
        context (str, optional): Contexte supplémentaire
        
    Returns:
        dict: Résultat de la requête
    """
    result = await client.process_query(query, context)
    return result

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
    import re  # Import déplacé ici
    
    # Variables locales au lieu d'utiliser la session Flask
    process_state = {
        'process_running': True,
        'last_code_generation_response': "",
        'reformulated_prompt': "",
        'project_structure': [],
        'tool_results': {},
        'url_contents': {},
        'last_api_call_time': 0,
    }
    
    # Fonction pour mettre à jour la progression
    def update_progress(step, message, progress=None):
        if progress_callback:
            progress_callback(step, message, progress)
        logging.info(f"[Étape {step}] {message}")
    
    # Initialiser le client MCP si les outils sont activés
    mcp_client = None
    if use_mcp_tools:
        from src.mcp.clients import SimpleMCPClient
        mcp_client = SimpleMCPClient(api_key, selected_model)
        update_progress(0, "🔌 Outils MCP activés: Recherche web, documentation, et composants frontend disponibles.")

    # == ÉTAPE 0: Extraction et traitement des URLs du prompt ==`
    update_progress(0, "Extraction des URLs du prompt...", 5)
    urls = extract_urls_from_prompt(user_prompt)
    url_context = ""
    
    if urls:
        update_progress(0, f"🔗 URLs détectées dans votre demande: {len(urls)} URL(s)", 10)
        try:
            url_contents = asyncio.run(process_urls(urls))
            process_state['url_contents'] = url_contents
            
            # Préparer le contexte des URLs
            url_context = "\n\n### CONTENU DES URLS FOURNIES ###\n"
            for url, content in url_contents.items():
                truncated_content = content[:5000] + "..." if len(content) > 5000 else content
                url_context += f"\nURL: {url}\n```\n{truncated_content}\n```\n"
            
            update_progress(0, f"✅ Contenu récupéré pour {len(url_contents)} URL(s)", 15)
        except Exception as e:
            update_progress(0, f"❌ Erreur lors de la récupération des URLs: {e}", 15)
            # Continuer même en cas d'erreur

    # == ÉTAPE 1: Reformulation du prompt ==`
    update_progress(1, "Reformulation du prompt...", 20)
    
    # Vérifier la limite de taux pour les modèles gratuits
    if is_free_model(selected_model):
        current_time = time.time()
        last_api_call_time = process_state.get('last_api_call_time', 0)
        time_since_last_call = current_time - last_api_call_time
        if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
            wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
            update_progress(1, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 20)
            time.sleep(wait_time)

    # Si les outils MCP sont activés, les utiliser pour améliorer le prompt
    additional_context = ""
    if use_mcp_tools and mcp_client:
        update_progress(1, "🔍 Utilisation des outils MCP pour analyser votre demande et recueillir des informations...", 25)
        
        # Ajouter les préférences frontend à la requête d'analyse
        frontend_preferences = ""
        if frontend_framework != "Auto-detect":
            frontend_preferences = f"Pour le frontend, utilisez {frontend_framework}. "
        if include_animations:
            frontend_preferences += "Incluez des animations CSS et des transitions pour rendre l'UI attrayante. "
        
        analysis_query = f"""
        Analysez cette demande de développement d'application: "{user_prompt}"
        
        1. Quel type d'application est demandé?
        2. Quels frameworks ou bibliothèques pourraient être nécessaires?
        3. Ai-je besoin de rechercher une documentation pour aider à l'implémentation?
        4. Quels composants frontend seraient utiles pour ce projet?
        5. Quel type de template conviendrait le mieux à cette application?
        
        {frontend_preferences}
        
        N'utilisez des outils que si nécessaire pour clarifier des détails techniques ou trouver des composants spécifiques.
        """
        
        # Exécuter la requête MCP de manière asynchrone
        mcp_result = asyncio.run(run_mcp_query(mcp_client, analysis_query))
        
        if mcp_result and "tool_calls" in mcp_result and mcp_result["tool_calls"]:
            update_progress(1, "✅ Outils utilisés pour recueillir du contexte supplémentaire pour votre projet.", 30)
            
            # Traiter et stocker les résultats des outils
            tool_results = {}
            for tool_call in mcp_result["tool_calls"]:
                tool_name = tool_call.get("tool")
                if tool_name:
                    tool_results[tool_name] = tool_call
            
            process_state['tool_results'] = tool_results
            
            # Ajouter ce contexte à notre prompt
            additional_context = f"""
            Contexte supplémentaire pour générer cette application:
            {mcp_result.get('text', '')}
            """
    else:
        # Si les outils MCP sont désactivés, informer clairement l'utilisateur
        if not use_mcp_tools:
            update_progress(1, "ℹ️ Outils MCP désactivés: Génération basique sans outils d'assistance.", 25)

    # Construction du prompt pour la reformulation uniquement
    prompt_reformulation = f"""
    Analysez la demande de l'utilisateur ci-dessous. Votre tâche est de:
    
    **Reformuler la Demande:** Créez un prompt détaillé et précis décrivant les fonctionnalités, technologies (supposez des technologies web standard comme Python/Flask ou Node/Express si non spécifié, ou utilisez HTML/CSS/JS si simple), et exigences. Cela guidera la génération de code. Incluez des commentaires dans le code généré.

    Demande de l'Utilisateur:
    "{user_prompt}"
    
    {url_context if url_context else ""}
    
    {additional_context if additional_context else ""}

    IMPORTANT: Si l'utilisateur a fourni des URLs, lisez attentivement leur contenu et suivez les instructions ou inspirez-vous des exemples qui y sont présents.

    IMPORTANT:Le format de sortie DOIT être EXACTEMENT comme suit:

    ### REFORMULATED PROMPT ###
    [Prompt reformulé détaillé ici]
    """
    messages_reformulation = [{"role": "user", "content": prompt_reformulation}]

    response_reformulation = call_openrouter_api(api_key, selected_model, messages_reformulation, temperature=0.6, max_retries=2)
    process_state['last_api_call_time'] = time.time()
    
    update_progress(1, "Analyse de la réponse de reformulation...", 35)
    
    reformulated_prompt = None
    if response_reformulation and response_reformulation.get("choices"):
        response_text = response_reformulation["choices"][0]["message"]["content"]
        
        # Extraire le prompt reformulé
        prompt_match = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if prompt_match:
            reformulated_prompt = prompt_match.group(1).strip()
            process_state['reformulated_prompt'] = reformulated_prompt
            # Stocker aussi dans app.config pour que app.py puisse le récupérer
            if current_app:
                current_app.config['reformulated_prompt'] = reformulated_prompt
            update_progress(1, "✅ Prompt reformulé avec succès.", 40)
        else:
            update_progress(1, "⚠️ Format de réponse inattendu pour la reformulation.", 40)
            # Utiliser la réponse complète comme fallback
            reformulated_prompt = response_text.strip()
            process_state['reformulated_prompt'] = reformulated_prompt
            if current_app:
                current_app.config['reformulated_prompt'] = reformulated_prompt
    else:
        update_progress(1, "❌ Échec de la reformulation du prompt.", 40)
        return False

    # == ÉTAPE 2: Définition de la structure ==`
    update_progress(2, "Définition de la structure du projet...", 45)
    
    # Vérifier la limite de taux pour les modèles gratuits
    if is_free_model(selected_model):
        current_time = time.time()
        last_api_call_time = process_state.get('last_api_call_time', 0)
        time_since_last_call = current_time - last_api_call_time
        if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
            wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
            update_progress(2, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 45)
            time.sleep(wait_time)
    
    # Construction du prompt pour la structure uniquement
    prompt_structure = f"""
    Basé sur le prompt reformulé ci-dessous, votre tâche est de:
    
    **Définir la Structure du Projet:** Proposez une structure complète et logique de fichiers/répertoires pour cette application. Listez chaque élément sur une nouvelle ligne. Utilisez des chemins relatifs. Marquez les répertoires avec un '/' final. N'incluez PAS de commentaires (#) ou de backticks (```) dans la liste de structure elle-même.

    Prompt reformulé:
    {reformulated_prompt}
    
    {url_context if url_context else ""}

    IMPORTANT: Si l'utilisateur a fourni des URLs, inspirez-vous des exemples ou de la structure qui y sont présents.

    Le format de sortie DOIT être exactement comme suit:

    ### STRUCTURE ###
    [Liste des fichiers/dossiers, un par ligne, ex.:
    src/
    src/main.py
    requirements.txt
    README.md]
    """
    messages_structure = [{"role": "user", "content": prompt_structure}]

    response_structure = call_openrouter_api(api_key, selected_model, messages_structure, temperature=0.6, max_retries=2)
    process_state['last_api_call_time'] = time.time()
    
    update_progress(2, "Analyse de la réponse de structure...", 50)
    
    structure_lines = []
    if response_structure and response_structure.get("choices"):
        response_text = response_structure["choices"][0]["message"]["content"]
        
        # Extraire la structure
        structure_match = re.search(r"###\s*STRUCTURE\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if structure_match:
            structure_block = structure_match.group(1).strip()
            # Nettoyage de la structure
            structure_block_cleaned = structure_block.strip().strip('`')
            potential_lines = structure_block_cleaned.split('\n')

            for line in potential_lines:
                line = line.strip()
                # Ignorer les lignes vides ou les marqueurs de code
                if not line or line == '```':
                    continue
                # Supprimer les commentaires
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                # Ajouter seulement si la ligne n'est pas vide après nettoyage
                if line:
                    structure_lines.append(line)
            
            process_state['project_structure'] = structure_lines
            update_progress(2, "✅ Structure du projet définie avec succès.", 55)
        else:
            update_progress(2, "⚠️ Format de réponse inattendu pour la structure.", 55)
            return False
    else:
        update_progress(2, "❌ Échec de la définition de la structure.", 55)
        return False

    # == ÉTAPE 3: Création de la Structure de Fichiers/Dossiers ==`
    update_progress(3, f"Création des dossiers et fichiers dans '{target_directory}'...", 60)
    created_paths = create_project_structure(target_directory, structure_lines)

    if created_paths is not None:
        update_progress(3, f"✅ Structure créée dans '{target_directory}'.", 65)

        # == ÉTAPE 4: Génération de Code ==`
        update_progress(4, "Génération du code complet...", 70)
        
        # Vérifier la limite de taux pour les modèles gratuits
        if is_free_model(selected_model):
            current_time = time.time()
            last_api_call_time = process_state.get('last_api_call_time', 0)
            time_since_last_call = current_time - last_api_call_time
            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                update_progress(4, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...", 70)
                time.sleep(wait_time)

        # --- Ajout d'instructions d'animation ---`
        animation_instruction = ""
        if include_animations and not prompt_mentions_design(user_prompt):
            animation_instruction = (
                "\n7. **Animation & Fluidité:** Puisqu'aucun design spécifique n'a été demandé, "
                "veuillez incorporer des animations CSS subtiles et des transitions (par exemple, effets hover, chargement/transitions fluides des sections, retour d'information subtil des boutons) "
                "pour rendre l'interface utilisateur moderne, fluide et attrayante. Privilégiez l'utilisabilité et évitez les animations trop distrayantes."
            )
            update_progress(4, "ℹ️ Aucune instruction de design détectée, ajout d'une demande d'animations fluides.", 75)
        
        # Ajouter les résultats des outils si disponibles
        tool_results_text = ""
        if use_mcp_tools and process_state.get('tool_results'):
            tool_results_text = "\n**Résultats des Outils:** Les informations suivantes ont été recueillies pour aider au développement:\n"
            for tool_name, tool_info in process_state['tool_results'].items():
                tool_results_text += f"\n- **{tool_name}**: {json.dumps(tool_info.get('args', {}))}\n"
                if 'result' in tool_info:
                    tool_results_text += f"Résultat: {tool_info['result'][:500]}...\n"
        
        # Contexte des URLs pour la génération de code
        url_reference = ""
        if process_state.get('url_contents'):
            url_reference = "\n**URLs fournies:** Veuillez vous référer aux URLs fournies par l'utilisateur comme source d'inspiration ou documentation. Suivez autant que possible les exemples ou la documentation fournie dans ces URLs."
        
        # Construction du prompt pour la génération de code avec les résultats des outils MCP
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

        # Utiliser des outils pour la génération de code si activés
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
            # Utiliser une température plus basse pour la génération de code sans outils
            response_code_gen = call_openrouter_api(
                api_key, 
                selected_model, 
                messages_code_gen, 
                temperature=0.4, 
                max_retries=2
            )
        process_state['last_api_call_time'] = time.time()

        if response_code_gen and response_code_gen.get("choices"):
            code_response_text = response_code_gen["choices"][0]["message"]["content"]
            
            # Vérifier les appels d'outils
            if use_mcp_tools and response_code_gen["choices"][0]["message"].get("tool_calls") and mcp_client:
                update_progress(4, "🔍 L'IA utilise des outils pour améliorer la génération de code...", 80)
                
                # Traiter chaque appel d'outil
                tool_calls = response_code_gen["choices"][0]["message"]["tool_calls"]
                for tool_call in tool_calls:
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    tool_args_str = function_info.get("arguments", "{}")
                    
                    try:
                        tool_args = json.loads(tool_args_str)
                        
                        # Exécuter l'outil via le client MCP
                        tool_query = f"Exécuter {tool_name} avec {tool_args}"
                        tool_result = asyncio.run(run_mcp_query(mcp_client, tool_query))
                        
                        if tool_result:
                            # Stocker les résultats des outils
                            if 'tool_results' not in process_state:
                                process_state['tool_results'] = {}
                            
                            process_state['tool_results'][tool_name] = {
                                "args": tool_args,
                                "result": tool_result.get("text", "")
                            }
                            
                            # Construire un prompt de suivi avec les résultats de l'outil
                            processed_result = handle_tool_results(tool_name, tool_result.get("text", ""))
                            
                            follow_up_prompt = f"""
                            J'ai utilisé {tool_name} pour recueillir des informations supplémentaires pour la génération de code.
                            
                            L'outil a retourné ces informations:
                            
                            {processed_result}
                            
                            Veuillez utiliser ces informations supplémentaires pour améliorer la génération de code.
                            Continuez à générer le code en utilisant le même format:
                            `--- FILE: chemin/vers/nomfichier ---`
                            
                            Et n'oubliez pas d'inclure tous les fichiers de la structure.
                            """
                            
                            # Faire un autre appel API avec le prompt de suivi
                            follow_up_messages = messages_code_gen + [
                                {"role": "assistant", "content": code_response_text},
                                {"role": "user", "content": follow_up_prompt}
                            ]
                            
                            update_progress(4, f"🔍 Utilisation des informations de {tool_name} pour améliorer le code...", 85)
                            
                            # Vérifier la limite de taux
                            if is_free_model(selected_model):
                                current_time = time.time()
                                time_since_last_call = time.time() - process_state.get('last_api_call_time', 0)
                                if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                    wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                    update_progress(4, f"⏳ Attente de {wait_time:.1f}s avant de continuer...", 85)
                                    time.sleep(wait_time)
                            
                            # Faire l'appel de suivi
                            follow_up_response = call_openrouter_api(
                                api_key, 
                                selected_model, 
                                follow_up_messages, 
                                temperature=0.4
                            )
                            process_state['last_api_call_time'] = time.time()
                            
                            if follow_up_response and follow_up_response.get("choices"):
                                # Mettre à jour la réponse de code avec la version améliorée
                                enhanced_code = follow_up_response["choices"][0]["message"]["content"]
                                code_response_text = enhanced_code
                    except Exception as e:
                        logging.warning(f"Erreur lors du traitement de l'outil {tool_name}: {e}")
            elif not use_mcp_tools and response_code_gen["choices"][0]["message"].get("tool_calls"):
                # Avertir que des outils ont été demandés mais sont désactivés
                update_progress(4, "⚠️ Le modèle a demandé des outils, mais les outils MCP sont désactivés. Les appels d'outils seront ignorés.", 80)
            
            process_state['last_code_generation_response'] = code_response_text
            update_progress(4, "✅ Réponse de génération de code reçue.", 90)

            # == ÉTAPE 5: Écriture du Code dans les Fichiers ==`
            update_progress(5, "Écriture du code dans les fichiers...", 90)
            files_written = []
            errors = []
            generation_incomplete = False
            
            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

            if files_written or errors:
                update_progress(5, "✅ Traitement de la réponse terminé.", 95)
                
                # Journaliser les résultats
                for f in files_written:
                    logging.info(f"📄 Fichier écrit: {Path(f).relative_to(Path(target_directory))}")
                for err in errors:
                    logging.error(f"❌ {err}")

                # == ÉTAPE 6: Vérifier les Fichiers Vides et Générer le Code Manquant ==`
                if not errors and (files_written or generation_incomplete):
                    update_progress(6, "Vérification des fichiers vides...", 95)
                    
                    empty_files = identify_empty_files(target_directory, structure_lines)
                    
                    if empty_files:
                        update_progress(6, f"Trouvé {len(empty_files)} fichiers vides qui nécessitent une génération de code.", 95)
                        
                        # Vérifier la limite de taux avant d'appeler l'API à nouveau
                        if is_free_model(selected_model):
                            current_time = time.time()
                            time_since_last_call = time.time() - process_state.get('last_api_call_time', 0)
                            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                update_progress(6, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes avant de générer le code manquant...", 95)
                                time.sleep(wait_time)
                        
                        update_progress(6, "Génération de code pour les fichiers vides...", 97)
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
                            update_progress(6, f"✅ Génération réussie de code pour {len(additional_files)} fichiers vides.", 98)
                            # Ajouter à la liste principale de fichiers
                            files_written.extend(additional_files)
                        
                        if additional_errors:
                            for err in additional_errors:
                                logging.error(f"❌ {err}")
                            # Ajouter à la liste principale d'erreurs
                            errors.extend(additional_errors)
                    else:
                        update_progress(6, "✅ Aucun fichier vide trouvé - tous les fichiers contiennent du code.", 98)
                
                # Message de succès final
                if not errors:
                    update_progress(7, "🎉 Application générée avec succès!", 100)
                    
                    # Sauvegarder le chemin pour le mode prévisualisation si on est dans un contexte Flask
                    if current_app:
                        current_app.config['last_generated_app_path'] = target_directory
                    
                    return True
                else:
                    update_progress(7, f"⚠️ Application générée avec {len(errors)} erreurs.", 100)
                    return len(files_written) > 0
            else:
                update_progress(5, "❌ Échec de l'écriture des fichiers.", 100)
                return False
        else:
            update_progress(4, "❌ Échec de la génération de code.", 100)
            return False
    else:
        update_progress(3, "❌ Échec de la création de la structure.", 100)
        return False


