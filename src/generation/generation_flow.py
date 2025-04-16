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
    if use_mcp_tools:
        from src.mcp.clients import SimpleMCPClient
        mcp_client = SimpleMCPClient(api_key, selected_model)
        update_progress(0, "🔌 Outils MCP activés: Recherche web, documentation, et composants frontend disponibles.", progress_callback)

    # == ÉTAPE 0: Extraction et traitement des URLs du prompt ==
    update_progress(0, "Extraction des URLs du prompt...", 5, progress_callback)
    urls = extract_urls_from_prompt(user_prompt)
    url_context = ""
    
    if urls:
        update_progress(0, f"🔗 URLs détectées dans votre demande: {len(urls)} URL(s)", 10, progress_callback)
        try:
            url_contents = asyncio.run(process_urls(urls))
            process_state['url_contents'] = url_contents
            
            # Préparer le contexte des URLs
            url_context = "\n\n### CONTENU DES URLS FOURNIES ###\n"
            for url, content in url_contents.items():
                truncated_content = content[:5000] + "..." if len(content) > 5000 else content
                url_context += f"\nURL: {url}\n```\n{truncated_content}\n```\n"
            
            update_progress(0, f"✅ Contenu récupéré pour {len(url_contents)} URL(s)", 15, progress_callback)
        except Exception as e:
            update_progress(0, f"❌ Erreur lors de la récupération des URLs: {e}", 15, progress_callback)
            # Continuer même en cas d'erreur

    # == ÉTAPE 1: Reformulation du prompt ==
    update_progress(1, "Reformulation du prompt...", 20, progress_callback)
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
        update_progress(1, "❌ Échec de la reformulation du prompt.", 40, progress_callback)
        return False

    # == ÉTAPE 2: Définition de la structure ==
    update_progress(2, "Définition de la structure du projet...", 45, progress_callback)
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

    # == ÉTAPE 3: Création de la Structure de Fichiers/Dossiers ==
    update_progress(3, f"Création des dossiers et fichiers dans '{target_directory}'...", 60, progress_callback)
    created_paths = create_project_structure(target_directory, structure_lines)

    if created_paths is not None:
        update_progress(3, f"✅ Structure créée dans '{target_directory}'.", 65, progress_callback)

        # == ÉTAPE 4: Génération de Code ==
        if include_animations and not prompt_mentions_design(user_prompt):
            animation_instruction = (
                "\n7. **Animation & Fluidité:** Puisqu'aucun design spécifique n'a été demandé, "
                "veuillez incorporer des animations CSS subtiles et des transitions (par exemple, effets hover, chargement/transitions fluides des sections, retour d'information subtil des boutons) "
                "pour rendre l'interface utilisateur moderne, fluide et attrayante. Privilégiez l'utilisabilité et évitez les animations trop distrayantes."
            )
            update_progress(4, "ℹ️ Aucune instruction de design détectée, ajout d'une demande d'animations fluides.", 75, progress_callback)
        if use_mcp_tools and process_state.get('tool_results'):
            tool_results_text = "\n**Résultats des Outils:** Les informations suivantes ont été recueillies pour aider au développement:\n"
            for tool_name, tool_info in process_state['tool_results'].items():
                tool_results_text += f"\n- **{tool_name}**: {json.dumps(tool_info.get('args', {}))}\n"
                if 'result' in tool_info:
                    tool_results_text += f"Résultat: {tool_info['result'][:500]}...\n"
        if process_state.get('url_contents'):
            url_reference = "\n**URLs fournies:** Veuillez vous référer aux URLs fournies par l'utilisateur comme source d'inspiration ou documentation. Suivez autant que possible les exemples ou la documentation fournie dans ces URLs."
        update_progress(4, "Génération du code complet...", 70, progress_callback)
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
            
            # Vérifier les appels d'outils
            if use_mcp_tools and response_code_gen["choices"][0]["message"].get("tool_calls") and mcp_client:
                update_progress(4, "🔍 L'IA utilise des outils pour améliorer la génération de code...", 80, progress_callback)
                
                tool_calls = response_code_gen["choices"][0]["message"]["tool_calls"]
                for tool_call in tool_calls:
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    tool_args_str = function_info.get("arguments", "{}")

                    if not tool_name: continue  # Ignorer si le nom de l'outil est manquant

                    try:
                        tool_args = json.loads(tool_args_str)

                        # Exécuter l'outil via le client MCP
                        tool_query = f"Exécuter {tool_name} avec {tool_args}"
                        tool_result = asyncio.run(run_mcp_query(mcp_client, tool_query))

                        if tool_result:
                            tool_result_text = tool_result.get("text", "")
                            extracted_details = None

                            # Extraire les URLs si c'est Web Search
                            if tool_name == 'Web Search':
                                # Regex simple pour trouver les URLs
                                urls_found = re.findall(r'https?://[^\s"\']+', tool_result_text)
                                extracted_details = list(set(urls_found))  # Liste unique d'URLs

                            # Enregistrer l'outil et ses détails (URLs pour Web Search)
                            add_used_tool(process_state, tool_name, extracted_details)

                            # Stocker les résultats bruts (peut être utile pour le débogage)
                            if 'tool_results' not in process_state:
                                process_state['tool_results'] = {}
                            process_state['tool_results'][tool_name] = {
                                "args": tool_args,
                                "result": tool_result_text  # Stocker le texte brut du résultat
                            }

                            # Construire un prompt de suivi avec les résultats de l'outil
                            processed_result = handle_tool_results(tool_name, tool_result_text)
                            # ... (le reste du traitement du résultat de l'outil et appel de suivi) ...

                    except Exception as e:
                        logging.warning(f"Erreur lors du traitement de l'outil {tool_name}: {e}")
                        add_used_tool(process_state, tool_name, {'error': str(e)})  # Enregistrer l'outil même en cas d'erreur

            process_state['last_code_generation_response'] = code_response_text
            update_progress(4, "✅ Réponse de génération de code reçue.", 90, progress_callback)

            # == ÉTAPE 5: Écriture du Code dans les Fichiers ==
            update_progress(5, "Écriture du code dans les fichiers...", 90, progress_callback)
            files_written = []
            errors = []
            generation_incomplete = False
            
            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

            if files_written or errors:
                update_progress(5, "✅ Traitement de la réponse terminé.", 95, progress_callback)
                
                # Journaliser les résultats
                for f in files_written:
                    logging.info(f"📄 Fichier écrit: {Path(f).relative_to(Path(target_directory))}")
                for err in errors:
                    logging.error(f"❌ {err}")

                # == ÉTAPE 6: Vérifier les Fichiers Vides et Générer le Code Manquant ==
                if not errors and (files_written or generation_incomplete):
                    update_progress(6, "Vérification des fichiers vides...", 95, progress_callback)
                    
                    empty_files = identify_empty_files(target_directory, structure_lines)
                    
                    if empty_files:
                        update_progress(6, f"Trouvé {len(empty_files)} fichiers vides qui nécessitent une génération de code.", 95, progress_callback)
                        
                        # Vérifier la limite de taux avant d'appeler l'API à nouveau
                        if is_free_model(selected_model):
                            current_time = time.time()
                            time_since_last_call = time.time() - process_state.get('last_api_call_time', 0)
                            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                update_progress(6, f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes avant de générer le code manquant...", 95, progress_callback)
                                time.sleep(wait_time)
                        
                        update_progress(6, "Génération de code pour les fichiers vides...", 97, progress_callback)
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
                            update_progress(6, f"✅ Génération réussie de code pour {len(additional_files)} fichiers vides.", 98, progress_callback)
                            # Ajouter à la liste principale de fichiers
                            files_written.extend(additional_files)
                        
                        if additional_errors:
                            for err in additional_errors:
                                logging.error(f"❌ {err}")
                            # Ajouter à la liste principale d'erreurs
                            errors.extend(additional_errors)
                    else:
                        update_progress(6, "✅ Aucun fichier vide trouvé - tous les fichiers contiennent du code.", 98, progress_callback)
                
                # Message de succès final
                if not errors:
                    update_progress(7, "🎉 Application générée avec succès!", 100, progress_callback)
                    
                    # Sauvegarder le chemin pour le mode prévisualisation si on est dans un contexte Flask
                    if current_app:
                        current_app.config['last_generated_app_path'] = target_directory
                        current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                    
                    return True
                else:
                    update_progress(7, f"⚠️ Application générée avec {len(errors)} erreurs.", 100, progress_callback)
                    if current_app:
                        current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                    return len(files_written) > 0
            else:
                update_progress(5, "❌ Échec de l'écriture des fichiers.", 100, progress_callback)
                if current_app:
                    current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
                return False
        else:
            update_progress(4, "❌ Échec de la génération de code.", 100, progress_callback)
            if current_app:
                current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
            return False
    else:
        update_progress(3, "❌ Échec de la création de la structure.", 100, progress_callback)
        if current_app:
            current_app.config['used_tools_details'] = process_state.get('used_tools_details', [])
        return False


