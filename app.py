import streamlit as st
import requests
import os
import time
import re
import json
from pathlib import Path

# --- Configuration ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-pro-exp-03-25:free" # Plus susceptible d'être dispo en free tier que 2.5 Pro
RATE_LIMIT_DELAY_SECONDS = 30 # Délai pour les modèles gratuits

# --- Fonctions Utilitaires ---

def is_free_model(model_name):
    """Vérifie si le nom du modèle indique un modèle gratuit nécessitant un délai."""
    # Adapté pour inclure Gemini Flash qui est souvent limité
    name_lower = model_name.lower()
    return ":free" in name_lower or "google/gemini-flash" in name_lower

def call_openrouter_api(api_key, model, messages, temperature=0.7, stream=False, max_retries=1):
    """Appelle l'API OpenRouter et gère les erreurs de base."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "CodeGenApp/1.0" # Bonne pratique d'identifier votre app
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream
    }
    response = None # Initialiser response à None
    
    for retry_attempt in range(max_retries + 1):  # +1 pour inclure la tentative initiale
        try:
            # Indiquer le numéro de tentative si ce n'est pas la première
            if retry_attempt > 0:
                st.info(f"🔄 Tentative #{retry_attempt+1}/{max_retries+1} d'appel à l'API...")
                
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=300) # Timeout long
            
            # Si pas d'erreur HTTP, on retourne la réponse JSON
            if response.status_code == 200:
                if retry_attempt > 0:
                    st.success(f"✅ Réussite après {retry_attempt+1} tentatives!")
                return response.json()
            
            # Si erreur 429 (Rate Limit), on tente d'extraire le retryDelay
            elif response.status_code == 429:
                # Afficher l'erreur et la réponse pour debug
                st.error(f"Erreur 429 (Rate Limit) à la tentative #{retry_attempt+1}")
                
                retry_delay = extract_retry_delay(response, model) 
                
                if retry_delay and retry_attempt < max_retries:
                    st.warning(f"⚠️ Erreur 429 (Rate Limit). Attente de {retry_delay} secondes avant nouvel essai...")
                    time.sleep(retry_delay)
                    continue  # Tenter à nouveau après le délai
                else:
                    if retry_attempt >= max_retries:
                        st.error(f"❌ Nombre maximum de tentatives atteint ({max_retries+1})")
                    else:
                        st.error("❌ Aucun délai de retry trouvé dans la réponse")
                    # Pas de retryDelay trouvé ou plus de tentatives possibles
                    response.raise_for_status()  # Déclenchera l'exception HTTPError
            else:
                # Autres codes d'erreur HTTP
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            st.error("Erreur : Le délai d'attente de la requête API a été dépassé (300 secondes). La génération est peut-être trop longue.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de l'appel API OpenRouter : {e}")
            if response is not None:
                try:
                    st.error(f"Réponse de l'API (status {response.status_code}): {response.text}")
                except Exception: # Au cas où response.text ne serait pas lisible
                     st.error(f"Réponse de l'API (status {response.status_code}) non décodable.")
            return None
        except json.JSONDecodeError:
            st.error(f"Erreur: Impossible de décoder la réponse JSON de l'API.")
            if response is not None:
               st.error(f"Réponse brute reçue : {response.text}")
            return None
    
    # Si on arrive ici, c'est que toutes les tentatives ont échoué
    return None

def extract_retry_delay(response, model):
    """Extrait le retryDelay d'une réponse d'erreur 429 de l'API."""
    try:
        # Afficher la réponse brute pour debug
        st.info("Analyse de la réponse d'erreur pour extraire le délai de retry...")
        
        # Tenter de parser la réponse JSON
        try:
            response_data = response.json()
            # Afficher la structure pour debug
            st.code(json.dumps(response_data, indent=2), language="json")
        except json.JSONDecodeError:
            st.warning("Réponse non-JSON reçue")
            response_data = {}
        
        # Méthode 1: Extraction directe via regex sur le texte brut
        # Cette méthode est plus robuste si la structure JSON est inattendue
        response_text = response.text
        retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', response_text)
        if retry_match:
            delay_num = int(retry_match.group(1))
            st.success(f"✅ Délai de retry extrait via regex: {delay_num}s (+1s)")
            return delay_num + 1
            
        # Méthode 2: Recherche dans la structure imbriquée (comme avant)
        # Structure possible 1: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"{...}","provider_name":"Google AI Studio"}}}
        if "error" in response_data and "metadata" in response_data["error"] and "raw" in response_data["error"]["metadata"]:
            raw_text = response_data["error"]["metadata"]["raw"]
            
            # Tentative d'extraction directe par regex dans le raw
            raw_retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', raw_text)
            if raw_retry_match:
                delay_num = int(raw_retry_match.group(1))
                st.success(f"✅ Délai de retry extrait du 'raw' via regex: {delay_num}s (+1s)")
                return delay_num + 1
            
            # Tentative de parsing JSON
            try:
                # Parfois le raw est un string JSON qui contient des caractères d'échappement
                # Nettoyage basique avant de parser
                if isinstance(raw_text, str):
                    raw_text = raw_text.replace('\\"', '"').replace('\\n', '\n')
                    
                nested_error = json.loads(raw_text)
                
                # Chercher RetryInfo dans les détails
                if "error" in nested_error and "details" in nested_error["error"]:
                    for detail in nested_error["error"]["details"]:
                        if "@type" in detail and "RetryInfo" in detail["@type"] and "retryDelay" in detail:
                            delay_str = detail["retryDelay"]
                            delay_match = re.search(r'(\d+)', delay_str)
                            if delay_match:
                                delay_num = int(delay_match.group(1))
                                st.success(f"✅ Délai de retry extrait du JSON 'raw': {delay_num}s (+1s)")
                                return delay_num + 1
            except Exception as e:
                st.warning(f"Échec du parsing du JSON dans 'raw': {e}")
                
        # Pas trouvé de retryDelay, retour au délai par défaut pour modèles gratuits
        if is_free_model(model):
            st.info(f"Aucun délai de retry spécifique trouvé. Utilisation du délai par défaut: {RATE_LIMIT_DELAY_SECONDS}s")
            return RATE_LIMIT_DELAY_SECONDS
        else:
            # Pour les modèles payants, utiliser un délai fixe de 30s comme fallback
            st.info("Modèle payant sans délai spécifié. Utilisation d'un délai standard de 30s.")
            return 30
        
    except Exception as e:
        st.warning(f"Impossible d'extraire le délai de retry: {e}")
        # Fallback: retourner 30 secondes pour être sûr
        return 30

def parse_structure_and_prompt(response_text):
    """Extrait le prompt reformulé et la structure nettoyée de la réponse du premier appel."""
    reformulated_prompt = None
    structure_lines = []
    cleaned_structure_lines = []

    try:
        # Recherche des marqueurs principaux
        prompt_match = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*?)\s*###\s*STRUCTURE\s*###", response_text, re.DOTALL | re.IGNORECASE)
        structure_match = re.search(r"###\s*STRUCTURE\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)

        if prompt_match:
            reformulated_prompt = prompt_match.group(1).strip()
        else:
            # Tentative de trouver le prompt même sans le marqueur structure après
            prompt_match_alt = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
            if prompt_match_alt:
                 reformulated_prompt = prompt_match_alt.group(1).strip()


        if structure_match:
            structure_block = structure_match.group(1).strip()
            # Nettoyage du bloc structure : enlever les ``` et les commentaires #
            structure_block_cleaned = structure_block.strip().strip('`') # Enlève les ``` au début/fin
            potential_lines = structure_block_cleaned.split('\n')

            for line in potential_lines:
                line = line.strip()
                # Ignorer lignes vides ou marqueurs de code seuls
                if not line or line == '```':
                    continue
                # Supprimer les commentaires inline (tout ce qui suit #)
                # Garder la partie avant le #, puis re-strip au cas où il y a des espaces avant #
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                # Ajouter seulement si la ligne n'est pas vide après nettoyage
                if line:
                    cleaned_structure_lines.append(line)
            structure_lines = cleaned_structure_lines # Utiliser la liste nettoyée
        else:
            # Si structure_match échoue, on ne peut pas extraire la structure
             st.warning("Marqueur '### STRUCTURE ###' non trouvé.")


        # --- Gestion des cas où les marqueurs ne sont pas trouvés ou vides ---
        if not reformulated_prompt and not structure_lines:
             st.error("Impossible d'extraire le prompt reformulé ET la structure. Vérifiez le format de réponse de l'IA.")
             st.code(response_text)
             return None, []
        elif not reformulated_prompt:
             st.warning("Prompt reformulé non trouvé, mais structure trouvée. Tentative de continuer.")
             # On pourrait essayer d'utiliser le prompt original comme fallback, mais c'est risqué
             # Pour l'instant, on retourne None pour le prompt, ce qui causera une erreur plus tard (ce qui est ok)
             return None, structure_lines
        elif not structure_lines:
             st.warning("Structure non trouvée, mais prompt reformulé trouvé. Impossible de créer les fichiers.")
             return reformulated_prompt, []


    except Exception as e:
        st.error(f"Erreur lors de l'analyse de la réponse de l'IA (structure/prompt) : {e}")
        st.code(response_text) # Afficher la réponse brute
        return None, []

    # Afficher la structure nettoyée pour le debug
    st.write("Structure détectée et nettoyée :")
    st.code("\n".join(structure_lines), language='text')

    return reformulated_prompt, structure_lines


def create_project_structure(base_path, structure_lines):
    """Crée les dossiers et les fichiers vides basés sur la structure NETTOYÉE fournie."""
    created_paths = []
    base_path = Path(base_path).resolve() # Obtenir le chemin absolu et normalisé
    st.info(f"Tentative de création de la structure dans : {base_path}")

    if not base_path.is_dir():
        st.error(f"Le chemin de base '{base_path}' n'est pas un dossier valide ou n'existe pas.")
        return None

    if not structure_lines:
        st.warning("Aucune ligne de structure fournie à créer.")
        return [] # Retourner une liste vide, ce n'est pas une erreur fatale

    try:
        for line in structure_lines:
            line = line.strip() # Re-nettoyer au cas où
            if not line: continue # Ignorer lignes vides

            # Sécurité: Vérifier la présence de '..' dans les composants du chemin
            relative_path = Path(line)
            if ".." in relative_path.parts:
                 st.warning(f"⚠️ Chemin contenant '..' ignoré (sécurité) : '{line}'")
                 continue

            item_path = base_path / relative_path

            try:
                # Déterminer si c'est un dossier ou un fichier
                # Path() supprime le '/' final, donc on se fie à la ligne originale
                is_dir = line.endswith('/')

                if is_dir:
                    # Créer le dossier
                    item_path.mkdir(parents=True, exist_ok=True)
                    st.write(f" ✅ Dossier créé/vérifié : {item_path}")
                    created_paths.append(item_path)
                else:
                    # C'est un fichier: Créer les dossiers parents si nécessaire
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    # Créer le fichier vide (ou le vider s'il existe)
                    item_path.touch(exist_ok=True)
                    st.write(f" ✅ Fichier créé/vérifié : {item_path}")
                    created_paths.append(item_path)

            except OSError as e:
                 st.error(f"❌ Erreur OS lors de la création de '{item_path}' depuis la ligne '{line}': {e}")
                 # Continuer avec les autres si possible
            except Exception as e:
                 st.error(f"❌ Erreur inattendue pour '{item_path}' depuis la ligne '{line}': {e}")

        return created_paths
    except Exception as e:
        st.error(f"Erreur majeure lors du traitement de la structure du projet : {e}")
        return None

def parse_and_write_code(base_path, code_response_text):
    """Analyse la réponse contenant le code et écrit chaque bloc dans le fichier correspondant."""
    base_path = Path(base_path).resolve()
    files_written = []
    errors = []
    generation_incomplete = False

    # Vérifier d'abord si la réponse se termine par le marqueur d'incomplétude
    if code_response_text.strip().endswith("GENERATION_INCOMPLETE"):
        generation_incomplete = True
        st.warning("⚠️ L'IA a indiqué que la génération de code est incomplète (limite de tokens probablement atteinte).")
        # Retirer le marqueur pour ne pas interférer avec le parsing du dernier fichier
        code_response_text = code_response_text.strip()[:-len("GENERATION_INCOMPLETE")].strip()

    # Regex pour trouver les blocs de code marqués par --- FILE: path/to/file ---
    # Utiliser re.split pour séparer par le marqueur, en capturant le chemin
    # Le `?` après `.*` le rend non-greedy, important si des marqueurs sont proches
    parts = re.split(r'(---\s*FILE:\s*(.*?)\s*---)', code_response_text, flags=re.IGNORECASE)

    if len(parts) <= 1:
        st.warning("Aucun marqueur '--- FILE: ... ---' trouvé dans la réponse de génération de code.")
        st.info("Tentative d'écriture de toute la réponse dans un fichier 'generated_code.txt'")
        output_file = base_path / "generated_code.txt"
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code_response_text)
            files_written.append(str(output_file))
            st.write(f" ✅ Code brut écrit dans : {output_file}")
        except Exception as e:
             errors.append(f"❌ Impossible d'écrire dans '{output_file}': {e}")
        # On ne peut pas savoir si c'est incomplet dans ce cas sans le marqueur
        return files_written, errors, generation_incomplete

    # Itérer sur les blocs capturés (ignore la première partie avant le premier marqueur)
    # Structure de parts: ['', marker1, path1, code1, marker2, path2, code2, ...]
    for i in range(1, len(parts), 3):
        try:
            # marker = parts[i] # Le marqueur complet (e.g., '--- FILE: src/main.py ---')
            file_path_str = parts[i+1].strip() # Le chemin du fichier extrait
            code_block = parts[i+2].strip()    # Le bloc de code (peut être vide si fin abrupte)

            if not file_path_str:
                st.warning(f"Marqueur trouvé mais chemin de fichier vide ou invalide, bloc ignoré.")
                continue

            # Nettoyage et validation du chemin
            file_path_str = file_path_str.replace('\r', '').strip()
            if not file_path_str: continue # Ignorer si vide après nettoyage

            relative_path = Path(file_path_str)
            if ".." in relative_path.parts: # Sécurité: Vérification de '..'
                 st.warning(f"⚠️ Chemin de fichier '{file_path_str}' contient '..', ignoré pour la sécurité.")
                 continue

            target_file_path = base_path / relative_path

            # S'assurer que le dossier parent existe (créé à l'étape 2, mais sécurité)
            target_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Écrire le code dans le fichier
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(code_block)

            files_written.append(str(target_file_path))
            # st.write(f"   Code écrit dans : {target_file_path}") # Peut être verbeux

        except IndexError:
             # Si la réponse se termine juste après un marqueur sans code
             st.warning(f"Fin de réponse inattendue après le marqueur pour '{parts[i+1].strip() if i+1 < len(parts) else 'dernier fichier'}'. Fichier potentiellement vide ou manquant.")
             continue
        except OSError as e:
            error_msg = f"❌ Erreur d'écriture dans le fichier '{file_path_str}': {e}"
            st.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"❌ Erreur inattendue lors du traitement du fichier '{file_path_str}': {e}"
            st.error(error_msg)
            errors.append(error_msg)

    return files_written, errors, generation_incomplete

def prompt_mentions_design(prompt_text):
    """Vérifie si le prompt utilisateur mentionne des termes liés au design."""
    keywords = [
        "design", "style", "css", "layout", "look", "feel", "appearance",
        "minimalist", "modern", "bootstrap", "tailwind", "material",
        "theme", "color", "font", "ui", "ux", "interface", "visual",
        "animation", "transition" # Inclure animation/transition ici
    ]
    prompt_lower = prompt_text.lower()
    for keyword in keywords:
        if keyword in prompt_lower:
            return True
    return False

# --- Interface Streamlit ---

st.set_page_config(layout="wide", page_title="CodeGen App")
st.title("✨ Générateur d'Application Web via IA ✨")
st.markdown("Décrivez votre application, fournissez un chemin, et laissez l'IA générer le code !")

# Utiliser st.session_state pour garder l'état entre les re-exécutions
if 'last_api_call_time' not in st.session_state:
    st.session_state.last_api_call_time = 0
if 'last_code_generation_response' not in st.session_state:
    st.session_state.last_code_generation_response = ""
if 'reformulated_prompt' not in st.session_state:
    st.session_state.reformulated_prompt = ""
if 'project_structure' not in st.session_state:
    st.session_state.project_structure = []
if 'process_running' not in st.session_state:
    st.session_state.process_running = False


# --- Inputs Utilisateur ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Clé API OpenRouter", type="password", help="Votre clé API OpenRouter. Elle ne sera pas stockée.")
    selected_model = st.text_input("Modèle OpenRouter", value=DEFAULT_MODEL, help=f"Ex: {DEFAULT_MODEL}, meta-llama/llama-3-70b-instruct, etc.")
    st.caption(f"Utilise l'API OpenRouter. Délai de {RATE_LIMIT_DELAY_SECONDS}s appliqué si modèle ':free' ou Gemini Flash détecté.")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Décrivez votre application")
    user_prompt = st.text_area(
        "Prompt initial:",
        height=200,
        placeholder="Exemple: Crée une simple application de TODO list en Flask avec une base de données SQLite. L'utilisateur doit pouvoir ajouter, voir et supprimer des tâches."
    )

with col2:
    st.header("2. Où générer le projet ?")
    target_directory = st.text_input(
        "Chemin du dossier de destination:",
        placeholder="Ex: C:\\Users\\VotreNom\\Projets\\MonAppGeneree",
        help="Le chemin absolu vers un dossier existant où le projet sera créé."
    )
    st.info("Assurez-vous que le dossier existe et que vous avez les permissions d'écriture.", icon="📁")

# Bouton de génération principal
generate_button = st.button("🚀 Générer l'application", type="primary", disabled=st.session_state.process_running)

st.markdown("---") # Séparateur visuel

# --- Logique Principale ---
if generate_button and not st.session_state.process_running:
    st.session_state.process_running = True # Empêcher double clic
    valid_input = True
    if not api_key:
        st.error("Veuillez entrer votre clé API OpenRouter dans la barre latérale.")
        valid_input = False
    if not user_prompt:
        st.error("Veuillez décrire l'application que vous souhaitez générer.")
        valid_input = False
    if not target_directory:
        st.error("Veuillez spécifier le chemin du dossier de destination.")
        valid_input = False
    elif not Path(target_directory).is_dir(): # Vérifier si le chemin est un dossier valide
         st.error(f"Le chemin spécifié '{target_directory}' n'est pas un dossier valide ou n'existe pas.")
         valid_input = False

    if valid_input:
        st.session_state.last_code_generation_response = "" # Reset state
        st.session_state.reformulated_prompt = ""
        st.session_state.project_structure = []

        # == ÉTAPE 1: Reformulation et Structure ==
        st.info("▶️ Étape 1: Reformulation du Prompt et Définition de la Structure...")
        status_placeholder_step1 = st.empty() # Pour afficher le statut
        with st.spinner("Appel à l'IA pour reformuler et définir la structure..."):

            # Vérifier le rate limit si modèle gratuit
            if is_free_model(selected_model):
                current_time = time.time()
                time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                    wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                    status_placeholder_step1.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (rate limit)...")
                    time.sleep(wait_time)

            # Construction du prompt pour la première étape
            prompt_step1 = f"""
            Analyze the user's request below. Your tasks are:
            1.  **Reformulate Request:** Create a detailed, precise prompt outlining features, technologies (assume standard web tech like Python/Flask or Node/Express if unspecified, or stick to HTML/CSS/JS if simple), and requirements. This will guide code generation. Include comments in generated code.
            2.  **Define Project Structure:** Propose a complete, logical file/directory structure. List each item on a new line. Use relative paths. Mark directories with a trailing '/'. DO NOT include comments (#) or backticks (```) in the structure list itself.

            User's Request:
            "{user_prompt}"

            Output format MUST be exactly as follows, starting immediately with the first marker:

            ### REFORMULATED PROMPT ###
            [Detailed reformulated prompt here]

            ### STRUCTURE ###
            [List files/folders, one per line, e.g.:
            src/
            src/main.py
            requirements.txt
            README.md]
            """
            messages_step1 = [{"role": "user", "content": prompt_step1}]

            response_step1 = call_openrouter_api(api_key, selected_model, messages_step1, temperature=0.6, max_retries=2)
            st.session_state.last_api_call_time = time.time() # Enregistrer le temps

        if response_step1 and response_step1.get("choices"):
            response_text_step1 = response_step1["choices"][0]["message"]["content"]
            reformulated_prompt, structure_lines = parse_structure_and_prompt(response_text_step1)

            if reformulated_prompt and structure_lines:
                st.session_state.reformulated_prompt = reformulated_prompt
                st.session_state.project_structure = structure_lines
                status_placeholder_step1.success("✅ Étape 1 terminée : Prompt reformulé et structure définie.")

                with st.expander("Voir le Prompt Reformulé et la Structure"):
                    st.subheader("Prompt Reformulé:")
                    st.markdown(f"```text\n{reformulated_prompt}\n```")
                    st.subheader("Structure du Projet Proposée (Nettoyée):")
                    st.code("\n".join(structure_lines), language='text')

                # == ÉTAPE 2: Création de la Structure de Fichiers/Dossiers ==
                st.info("▶️ Étape 2: Création de la Structure Physique...")
                status_placeholder_step2 = st.empty()
                with st.spinner(f"Création des dossiers et fichiers dans '{target_directory}'..."):
                    created_paths = create_project_structure(target_directory, st.session_state.project_structure)

                if created_paths is not None:
                    status_placeholder_step2.success(f"✅ Étape 2 terminée : Structure créée dans '{target_directory}'.")

                    # == ÉTAPE 3: Génération du Code ==
                    st.info("▶️ Étape 3: Génération du Code Complet...")
                    status_placeholder_step3 = st.empty()
                    with st.spinner("Appel à l'IA pour générer le code (cela peut prendre du temps)..."):

                        # Vérifier le rate limit si modèle gratuit
                        if is_free_model(selected_model):
                           current_time = time.time()
                           time_since_last_call = current_time - st.session_state.get('last_api_call_time', 0)
                           if time_since_last_call < RATE_LIMIT_DELAY_SECONDS:
                               wait_time = RATE_LIMIT_DELAY_SECONDS - time_since_last_call
                               status_placeholder_step3.warning(f"⏳ Modèle gratuit détecté. Attente de {wait_time:.1f} secondes (rate limit)...")
                               time.sleep(wait_time)

                        # --- Ajout de l'instruction pour les animations ---
                        animation_instruction = ""
                        if not prompt_mentions_design(user_prompt):
                             animation_instruction = (
                                 "\n7. **Animation & Fluidity:** Since no specific design was requested, "
                                 "please incorporate subtle CSS animations and transitions (e.g., hover effects, smooth section loading/transitions, subtle button feedback) "
                                 "to make the user interface feel modern, fluid, and engaging. Prioritize usability and avoid overly distracting animations."
                             )
                             st.info("ℹ️ Aucune instruction de design détectée, ajout de la demande d'animations fluides.")

                        # Construction du prompt pour la génération de code
                        prompt_step2 = f"""
                        Generate the *complete* code for the application based on the prompt and structure below.

                        **Detailed Prompt:**
                        {st.session_state.reformulated_prompt}

                        **Project Structure (for reference only):**
                        ```
                        {chr(10).join(st.session_state.project_structure)}
                        ```

                        **Instructions:**
                        1. Provide the full code for *all* files listed in the structure.
                        2. Use the EXACT format `--- FILE: path/to/filename ---` on a line by itself before each file's code block. Start the response *immediately* with the first marker. No introductory text.
                        3. Ensure code is functional, includes imports, basic error handling, and comments.
                        4. For `requirements.txt` or similar, list dependencies.
                        5. For `README.md`, provide setup/run instructions.
                        6. If the code exceeds token limits, end the *entire* response *exactly* with: `GENERATION_INCOMPLETE` (no other text after).{animation_instruction}

                        Generate the code now:
                        """
                        messages_step2 = [{"role": "user", "content": prompt_step2}]

                        # Utiliser une température plus basse pour le code pour moins de créativité/erreurs
                        response_step2 = call_openrouter_api(api_key, selected_model, messages_step2, temperature=0.4, max_retries=2)
                        st.session_state.last_api_call_time = time.time()

                    if response_step2 and response_step2.get("choices"):
                        code_response_text = response_step2["choices"][0]["message"]["content"]
                        st.session_state.last_code_generation_response = code_response_text # Store for display
                        status_placeholder_step3.success("✅ Étape 3 terminée : Réponse de génération de code reçue.")

                        # == ÉTAPE 4: Écriture du Code dans les Fichiers ==
                        st.info("▶️ Étape 4: Écriture du Code dans les Fichiers...")
                        status_placeholder_step4 = st.empty()
                        files_written = []
                        errors = []
                        generation_incomplete = False
                        with st.spinner("Analyse de la réponse et écriture du code..."):
                            files_written, errors, generation_incomplete = parse_and_write_code(target_directory, code_response_text)

                        if files_written or errors:
                            status_placeholder_step4.success(f"✅ Étape 4 terminée : Traitement de la réponse terminé.")
                            st.subheader("Résultat de l'écriture des fichiers :")
                            for f in files_written:
                                st.success(f"   📄 Fichier écrit : {Path(f).relative_to(Path(target_directory))}")
                            for err in errors:
                                st.error(f"   ❌ {err}")

                            if not errors and not generation_incomplete:
                                st.success("🎉 Application générée avec succès !")
                                st.balloons()
                            elif generation_incomplete:
                                 st.warning("⚠️ La génération est incomplète. Le code généré jusqu'à présent a été écrit. Vous devrez peut-être ecrire la suite manuellement.")
                            elif errors:
                                st.error("❗️ Des erreurs se sont produites lors de l'écriture de certains fichiers.")

                        else:
                             status_placeholder_step4.error("❌ Étape 4 échouée : Aucun fichier n'a pu être écrit.")


                    else:
                        status_placeholder_step3.error("❌ Étape 3 échouée : Échec de la récupération de la génération de code.")
                        if response_step2: st.json(response_step2) # Afficher la réponse d'erreur si dispo

                else: # Erreur lors de la création de la structure (gérée dans la fonction)
                   status_placeholder_step2.error("❌ Étape 2 échouée : Impossible de créer la structure du projet.")

            else: # Erreur lors du parsing de l'étape 1
                status_placeholder_step1.error("❌ Étape 1 échouée : Impossible d'analyser la réponse de l'IA (prompt/structure).")
                if 'response_text_step1' in locals():
                    with st.expander("Voir la réponse brute de l'Étape 1"):
                        st.code(response_text_step1, language='text')
        else: # Erreur lors de l'appel API de l'étape 1
             status_placeholder_step1.error("❌ Étape 1 échouée : Échec de l'appel API pour la reformulation/structure.")
             if response_step1: st.json(response_step1) # Afficher la réponse d'erreur si dispo

        st.session_state.process_running = False # Réactiver le bouton
        st.info("🏁 Processus terminé.") # Indiquer la fin globale

    else: # Input invalide
        st.session_state.process_running = False # Réactiver le bouton si erreur input


# Option pour afficher le dernier code généré (utile si incomplet ou pour debug)
if st.session_state.last_code_generation_response:
     st.markdown("---")
     with st.expander("Voir le dernier code brut généré par l'IA (Étape 3)", expanded=False):
         st.code(st.session_state.last_code_generation_response, language='markdown')