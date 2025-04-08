"""
Module de gestion du processus de génération d'applications.
Contient les étapes et la logique de génération d'applications.
"""
import time
import asyncio
import json
import streamlit as st
from pathlib import Path

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
from src.utils.prompt_utils import prompt_mentions_design
from src.mcp.tool_utils import get_default_tools
from src.mcp.handlers import handle_tool_results
from src.preview.preview_manager import launch_preview_mode

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

def generate_application(api_key, selected_model, user_prompt, target_directory, use_mcp_tools=True, frontend_framework="Auto-detect", include_animations=True):
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
        
    Returns:
        bool: True si la génération a réussi, False sinon
    """
    st.session_state.process_running = True  # Empêcher le double-clic
    st.session_state.last_code_generation_response = ""  # Réinitialiser l'état
    st.session_state.reformulated_prompt = ""
    st.session_state.project_structure = []
    st.session_state.tool_results = {}
    
    # Initialiser le client MCP si les outils sont activés
    if use_mcp_tools:
        from src.mcp.clients import SimpleMCPClient
        st.session_state.mcp_client = SimpleMCPClient(api_key, selected_model)
        st.info("🔌 Outils MCP activés: Recherche web, documentation, et composants frontend disponibles.")

    # == ÉTAPE 1: Reformulation et Structure ==
    st.info("▶️ Étape 1: Reformulation du prompt et définition de la structure...")
    status_placeholder_step1 = st.empty()  # Pour afficher le statut
    with st.spinner("Appel de l'IA pour reformuler et définir la structure..."):
        # Vérifier la limite de taux pour les modèles gratuits
        if is_free_model(selected_model):
            current_time = time.time()
            time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
            if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                status_placeholder_step1.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...")
                time.sleep(wait_time)

        # Si les outils MCP sont activés, les utiliser pour améliorer le prompt
        additional_context = ""
        if use_mcp_tools and st.session_state.mcp_client:
            status_placeholder_step1.info("🔍 Utilisation des outils MCP pour analyser votre demande et recueillir des informations...")
            
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
            mcp_result = asyncio.run(run_mcp_query(st.session_state.mcp_client, analysis_query))
            
            if mcp_result and "tool_calls" in mcp_result and mcp_result["tool_calls"]:
                status_placeholder_step1.success("✅ Outils utilisés pour recueillir du contexte supplémentaire pour votre projet.")
                
                # Traiter et stocker les résultats des outils
                for tool_call in mcp_result["tool_calls"]:
                    tool_name = tool_call.get("tool")
                    if tool_name:
                        st.session_state.tool_results[tool_name] = tool_call
                
                # Ajouter ce contexte à notre prompt
                additional_context = f"""
                Contexte supplémentaire pour générer cette application:
                {mcp_result.get('text', '')}
                """
            
        # Construction du prompt pour la première étape
        prompt_step1 = f"""
        Analysez la demande de l'utilisateur ci-dessous. Vos tâches sont:
        1.  **Reformuler la Demande:** Créez un prompt détaillé et précis décrivant les fonctionnalités, technologies (supposez des technologies web standard comme Python/Flask ou Node/Express si non spécifié, ou utilisez HTML/CSS/JS si simple), et exigences. Cela guidera la génération de code. Incluez des commentaires dans le code généré.
        2.  **Définir la Structure du Projet:** Proposez une structure complète et logique de fichiers/répertoires. Listez chaque élément sur une nouvelle ligne. Utilisez des chemins relatifs. Marquez les répertoires avec un '/' final. N'incluez PAS de commentaires (#) ou de backticks (```) dans la liste de structure elle-même.

        Demande de l'Utilisateur:
        "{user_prompt}"
        
        {additional_context if additional_context else ""}

        Le format de sortie DOIT être exactement comme suit, en commençant immédiatement par le premier marqueur:

        ### REFORMULATED PROMPT ###
        [Prompt reformulé détaillé ici]

        ### STRUCTURE ###
        [Liste des fichiers/dossiers, un par ligne, ex.:
        src/
        src/main.py
        requirements.txt
        README.md]
        """
        messages_step1 = [{"role": "user", "content": prompt_step1}]

        response_step1 = call_openrouter_api(api_key, selected_model, messages_step1, temperature=0.6, max_retries=2)
        st.session_state.last_api_call_time = time.time()  # Enregistrer l'heure

    if response_step1 and response_step1.get("choices"):
        response_text_step1 = response_step1["choices"][0]["message"]["content"]
        reformulated_prompt, structure_lines = parse_structure_and_prompt(response_text_step1)

        if reformulated_prompt and structure_lines:
            st.session_state.reformulated_prompt = reformulated_prompt
            st.session_state.project_structure = structure_lines
            status_placeholder_step1.success("✅ Étape 1 terminée: Prompt reformulé et structure définie.")

            with st.expander("Voir le Prompt Reformulé et la Structure"):
                st.subheader("Prompt Reformulé:")
                st.markdown(f"```text\n{reformulated_prompt}\n```")
                st.subheader("Structure de Projet Proposée (Nettoyée):")
                st.code("\n".join(structure_lines), language='text')

            # == ÉTAPE 2: Création de la Structure de Fichiers/Dossiers ==
            st.info("▶️ Étape 2: Création de la Structure Physique...")
            status_placeholder_step2 = st.empty()
            with st.spinner(f"Création des dossiers et fichiers dans '{target_directory}'..."):
                created_paths = create_project_structure(target_directory, st.session_state.project_structure)

            if created_paths is not None:
                status_placeholder_step2.success(f"✅ Étape 2 terminée: Structure créée dans '{target_directory}'.")

                # == ÉTAPE 3: Génération de Code ==
                st.info("▶️ Étape 3: Génération du Code Complet...")
                status_placeholder_step3 = st.empty()
                with st.spinner("Appel de l'IA pour générer le code (cela peut prendre du temps)..."):
                    # Vérifier la limite de taux pour les modèles gratuits
                    if is_free_model(selected_model):
                       current_time = time.time()
                       time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                       if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                           wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                           status_placeholder_step3.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (limite de taux)...")
                           time.sleep(wait_time)

                    # --- Ajout d'instructions d'animation ---
                    animation_instruction = ""
                    if not prompt_mentions_design(user_prompt):
                         animation_instruction = (
                             "\n7. **Animation & Fluidité:** Puisqu'aucun design spécifique n'a été demandé, "
                             "veuillez incorporer des animations CSS subtiles et des transitions (par exemple, effets hover, chargement/transitions fluides des sections, retour d'information subtil des boutons) "
                             "pour rendre l'interface utilisateur moderne, fluide et attrayante. Privilégiez l'utilisabilité et évitez les animations trop distrayantes."
                         )
                         st.info("ℹ️ Aucune instruction de design détectée, ajout d'une demande d'animations fluides.")
                    
                    # Ajouter les résultats des outils si disponibles
                    tool_results_text = ""
                    if use_mcp_tools and st.session_state.tool_results:
                        tool_results_text = "\n**Résultats des Outils:** Les informations suivantes ont été recueillies pour aider au développement:\n"
                        for tool_name, tool_info in st.session_state.tool_results.items():
                            st.write(f"**{tool_name}**")
                            st.write(f"Arguments: {tool_info.get('args', {})}")
                            if 'result' in tool_info:
                                with st.expander(f"Voir les résultats de {tool_name}"):
                                    st.code(tool_info['result'])
                    
                    # Construction du prompt pour la génération de code avec les résultats des outils MCP
                    prompt_step2 = f"""
                    Générez le code *complet* de l'application basé sur le prompt et la structure ci-dessous.

                    **Prompt Détaillé:**
                    {st.session_state.reformulated_prompt}
                    
                    {tool_results_text if tool_results_text else ""}

                    **Structure du Projet (uniquement pour référence):**
                    ```
                    {chr(10).join(st.session_state.project_structure)}
                    ```

                    **Instructions:**
                    1. Fournissez le code complet pour *tous* les fichiers listés dans la structure.
                    2. Utilisez le format EXACT `--- FILE: chemin/vers/nomfichier ---` sur une ligne par lui-même avant chaque bloc de code de fichier. Commencez la réponse *immédiatement* avec le premier marqueur. Aucun texte d'introduction.
                    3. Assurez-vous que le code est fonctionnel, inclut les imports, la gestion des erreurs de base et des commentaires.
                    4. Pour `requirements.txt` ou similaire, listez les dépendances.
                    5. Pour `README.md`, fournissez des instructions de configuration/exécution.
                    6. Si le code dépasse les limites de jetons, terminez la réponse *entière* *exactement* avec: `GENERATION_INCOMPLETE` (aucun autre texte après).{animation_instruction}

                    Générez le code maintenant:
                    """
                    messages_step2 = [{"role": "user", "content": prompt_step2}]

                    # Utiliser des outils pour la génération de code si activés
                    if use_mcp_tools:
                        response_step2 = call_openrouter_api(
                            api_key, 
                            selected_model, 
                            messages_step2, 
                            temperature=0.4, 
                            max_retries=2,
                            tools=get_default_tools()
                        )
                    else:
                        # Utiliser une température plus basse pour la génération de code (moins de créativité/erreurs)
                        response_step2 = call_openrouter_api(
                            api_key, 
                            selected_model, 
                            messages_step2, 
                            temperature=0.4, 
                            max_retries=2
                        )
                    st.session_state.last_api_call_time = time.time()

                if response_step2 and response_step2.get("choices"):
                    code_response_text = response_step2["choices"][0]["message"]["content"]
                    
                    # Vérifier les appels d'outils
                    if use_mcp_tools and response_step2["choices"][0]["message"].get("tool_calls"):
                        status_placeholder_step3.info("🔍 L'IA utilise des outils pour améliorer la génération de code...")
                        
                        # Traiter chaque appel d'outil
                        tool_calls = response_step2["choices"][0]["message"]["tool_calls"]
                        for tool_call in tool_calls:
                            function_info = tool_call.get("function", {})
                            tool_name = function_info.get("name")
                            tool_args_str = function_info.get("arguments", "{}")
                            
                            try:
                                tool_args = json.loads(tool_args_str)
                                
                                # Exécuter l'outil via le client MCP
                                tool_query = f"Exécuter {tool_name} avec {tool_args}"
                                tool_result = asyncio.run(run_mcp_query(st.session_state.mcp_client, tool_query))
                                
                                if tool_result:
                                    # Stocker les résultats des outils
                                    st.session_state.tool_results[tool_name] = {
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
                                    follow_up_messages = messages_step2 + [
                                        {"role": "assistant", "content": code_response_text},
                                        {"role": "user", "content": follow_up_prompt}
                                    ]
                                    
                                    status_placeholder_step3.info(f"🔍 Utilisation des informations de {tool_name} pour améliorer le code...")
                                    
                                    # Vérifier la limite de taux
                                    if is_free_model(selected_model):
                                        current_time = time.time()
                                        time_since_last_call = time.time() - st.session_state.get('last_api_call_time', 0)
                                        if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                            wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                            st.warning(f"⏳ Attente de {wait_time:.1f}s avant de continuer...")
                                            time.sleep(wait_time)
                                    
                                    # Faire l'appel de suivi
                                    follow_up_response = call_openrouter_api(
                                        api_key, 
                                        selected_model, 
                                        follow_up_messages, 
                                        temperature=0.4
                                    )
                                    st.session_state.last_api_call_time = time.time()
                                    
                                    if follow_up_response and follow_up_response.get("choices"):
                                        # Mettre à jour la réponse de code avec la version améliorée
                                        enhanced_code = follow_up_response["choices"][0]["message"]["content"]
                                        code_response_text = enhanced_code
                            except Exception as e:
                                st.warning(f"Erreur lors du traitement de l'outil {tool_name}: {e}")
                    
                    st.session_state.last_code_generation_response = code_response_text  # Stocker pour affichage
                    status_placeholder_step3.success("✅ Étape 3 terminée: Réponse de génération de code reçue.")

                    # == ÉTAPE 4: Écriture du Code dans les Fichiers ==
                    st.info("▶️ Étape 4: Écriture du Code dans les Fichiers...")
                    status_placeholder_step4 = st.empty()
                    files_written = []
                    errors = []
                    generation_incomplete = False
                    with st.spinner("Analyse de la réponse et écriture du code..."):
                        files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

                    if files_written or errors:
                        status_placeholder_step4.success(f"✅ Étape 4 terminée: Traitement de la réponse terminé.")
                        st.subheader("Résultats de l'écriture de fichiers:")
                        for f in files_written:
                            st.success(f"   📄 Fichier écrit: {Path(f).relative_to(Path(target_directory))}")
                        for err in errors:
                            st.error(f"   ❌ {err}")

                        # == ÉTAPE 5: Vérifier les Fichiers Vides et Générer le Code Manquant ==
                        empty_files_check = st.checkbox("Vérifier les fichiers vides et générer leur code", value=True)
                        
                        if empty_files_check and not errors and (files_written or generation_incomplete):
                            st.info("▶️ Étape 5: Vérification des fichiers vides et génération du code manquant...")
                            status_placeholder_step5 = st.empty()
                            
                            with st.spinner("Identification des fichiers vides..."):
                                empty_files = identify_empty_files(target_directory, st.session_state.project_structure)
                            
                            if empty_files:
                                status_placeholder_step5.warning(f"Trouvé {len(empty_files)} fichiers vides qui nécessitent une génération de code.")
                                st.write("Fichiers vides:")
                                for ef in empty_files:
                                    st.info(f"   📄 Fichier vide: {ef}")
                                
                                # Vérifier la limite de taux avant d'appeler l'API à nouveau
                                if is_free_model(selected_model):
                                    current_time = time.time()
                                    time_since_last_call = time.time() - st.session_state.get('last_api_call_time', 0)
                                    if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                                        wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                                        st.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes avant de générer le code manquant...")
                                        time.sleep(wait_time)
                                
                                with st.spinner("Génération de code pour les fichiers vides..."):
                                    additional_files, additional_errors = generate_missing_code(
                                        api_key, 
                                        selected_model, 
                                        empty_files, 
                                        st.session_state.reformulated_prompt, 
                                        st.session_state.project_structure,
                                        st.session_state.last_code_generation_response,
                                        target_directory
                                    )
                                    st.session_state.last_api_call_time = time.time()
                                
                                if additional_files:
                                    status_placeholder_step5.success(f"✅ Génération réussie de code pour {len(additional_files)} fichiers vides.")
                                    st.subheader("Fichiers supplémentaires remplis:")
                                    for f in additional_files:
                                        st.success(f"   📄 Fichier rempli: {Path(f).relative_to(Path(target_directory))}")
                                    
                                    # Ajouter à la liste principale de fichiers
                                    files_written.extend(additional_files)
                                
                                if additional_errors:
                                    for err in additional_errors:
                                        st.error(f"   ❌ {err}")
                                    
                                    # Ajouter à la liste principale d'erreurs
                                    errors.extend(additional_errors)
                            else:
                                status_placeholder_step5.success("✅ Aucun fichier vide trouvé - tous les fichiers contiennent du code.")
                        
                        # Afficher les résultats des outils si des outils ont été utilisés
                        if use_mcp_tools and st.session_state.tool_results:
                            with st.expander("Voir les Résultats des Outils MCP"):
                                st.subheader("🔍 Résultats des Outils Utilisés")
                                for tool_name, tool_info in st.session_state.tool_results.items():
                                    st.write(f"**{tool_name}**")
                                    st.write(f"Arguments: {tool_info.get('args', {})}")
                                    if 'result' in tool_info:
                                        with st.expander(f"Voir les résultats de {tool_name}"):
                                            st.code(tool_info['result'])
                        
                        # Message de succès final
                        if not errors:
                            st.success("🎉 Application générée avec succès!")
                            st.balloons()
                            
                            # Sauvegarder le chemin pour le mode prévisualisation
                            st.session_state.last_generated_app_path = target_directory
                            
                            # Ajouter le bouton de prévisualisation
                            preview_col1, preview_col2 = st.columns([3, 1])
                            with preview_col1:
                                st.info("Voulez-vous prévisualiser l'application générée directement dans l'interface?")
                            with preview_col2:
                                if st.button("🔍 Prévisualiser l'application", type="primary"):
                                    # Définir les états de session pour la prévisualisation
                                    launch_preview_mode(target_directory)
                                    # Force le rechargement complet de l'application
                                    st.experimental_rerun()
                            return True
                        elif len(errors) < len(files_written) / 2:  # Si les erreurs sont inférieures à la moitié des fichiers
                            st.warning("🎯 Application générée avec quelques erreurs. Vérifiez les messages d'erreur ci-dessus.")
                            
                            # Proposer quand même la prévisualisation mais avec un avertissement
                            st.session_state.last_generated_app_path = target_directory
                            preview_col1, preview_col2 = st.columns([3, 1])
                            with preview_col1:
                                st.warning("L'application a été générée avec des erreurs. La prévisualisation pourrait ne pas fonctionner correctement.")
                            with preview_col2:
                                if st.button("🔍 Tenter la prévisualisation", type="primary"):
                                    # Définir les états de session pour la prévisualisation
                                    launch_preview_mode(target_directory)
                                    # Force le rechargement complet de l'application
                                    st.experimental_rerun()
                            return True
                        else:
                            st.error("❗️ Plusieurs erreurs se sont produites pendant la génération de l'application.")
                            return False

                    else:
                         status_placeholder_step4.error("❌ Étape 4 échouée: Aucun fichier n'a pu être écrit.")
                         return False

                else:
                    status_placeholder_step3.error("❌ Étape 3 échouée: Échec de la récupération de la génération de code.")
                    if response_step2: st.json(response_step2)  # Afficher la réponse d'erreur si disponible
                    return False

            else:  # Erreur lors de la création de la structure (gérée dans la fonction)
               status_placeholder_step2.error("❌ Étape 2 échouée: Impossible de créer la structure du projet.")
               return False

        else:  # Erreur lors de l'analyse de l'étape 1
            status_placeholder_step1.error("❌ Étape 1 échouée: Impossible d'analyser la réponse de l'IA (prompt/structure).")
            if 'response_text_step1' in locals():
                with st.expander("Voir la réponse brute de l'Étape 1"):
                    st.code(response_text_step1, language='text')
            return False
    else:  # Erreur lors de l'appel API à l'étape 1
         status_placeholder_step1.error("❌ Étape 1 échouée: Échec de l'appel API pour la reformulation/structure.")
         if response_step1: st.json(response_step1)  # Afficher la réponse d'erreur si disponible
         return False

    st.session_state.process_running = False  # Réactiver le bouton
    st.info("🏁 Processus terminé.")  # Indiquer la fin globale
    return True