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
Module pour l'interaction avec l'API OpenRouter.
Gère les appels à l'API, le traitement des réponses et la gestion des erreurs.
"""

import os
import re
import json
import time
import requests
import logging
from typing import Dict, List, Any, Optional
from src.config.constants import OPENROUTER_API_URL
from src.utils.model_utils import is_free_model

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def call_openrouter_api(api_key, model, messages, temperature=0.7, stream=False, max_retries=1, tools=None, response_format=None):
    """
    Call the OpenRouter API and handle basic errors.
    
    Args:
        api_key (str): OpenRouter API key
        model (str): Model name to use
        messages (list): List of message objects
        temperature (float): Temperature parameter for generation
        stream (bool): Whether to stream the response
        max_retries (int): Maximum number of retries on failure
        tools (list, optional): List of tool definitions to include in the request
        response_format (str, optional): Desired response format for structured output
        
    Returns:
        dict: JSON response or None on error
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "CodeGenApp/1.0" # Good practice to identify your app
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream
    }
    
    # Add tools if provided
    if tools:
        data["tools"] = tools
    
    # Add response_format if provided (for structured output)
    if response_format:
        data["response_format"] = response_format
    
    response = None # Initialize response to None
    
    for retry_attempt in range(max_retries + 1):  # +1 to include initial attempt
        try:
            # Indicate attempt number if not the first one
            if retry_attempt > 0:
                logger.info(f"Attempt #{retry_attempt+1}/{max_retries+1} calling API...")
                
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=300) # Long timeout
            
            # If no HTTP error, return JSON response
            if response.status_code == 200:
                if retry_attempt > 0:
                    logger.info(f"Success after {retry_attempt+1} attempts!")
                return response.json()
            
            # If error 429 (Rate Limit), try to extract retryDelay
            elif response.status_code == 429:
                # Show error and response for debug
                logger.error(f"Error 429 (Rate Limit) on attempt #{retry_attempt+1}")
                
                retry_delay = extract_retry_delay(response, model) 
                
                if retry_delay and retry_attempt < max_retries:
                    logger.warning(f"Rate Limit hit. Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                    continue  # Try again after delay
                else:
                    if retry_attempt >= max_retries:
                        logger.error(f"Maximum number of attempts reached ({max_retries+1})")
                    else:
                        logger.error("No retry delay found in response")
                    # No retryDelay found or no more attempts possible
                    response.raise_for_status()  # Will trigger HTTPError exception
            else:
                # Other HTTP error codes
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            logger.error("Error: API request timeout exceeded (300 seconds). Generation might be too long.")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during OpenRouter API call: {e}")
            if response is not None:
                try:
                    logger.error(f"API response (status {response.status_code}): {response.text}")
                except Exception: # In case response.text isn't readable
                     logger.error(f"API response (status {response.status_code}) not decodable.")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error: Unable to decode JSON response from API.")
            if response is not None:
               logger.error(f"Raw response received: {response.text}")
            return None
    
    # If we get here, all attempts failed
    return None

def extract_retry_delay(response, model):
    """
    Extract the retryDelay from a 429 error response.
    
    Args:
        response (Response): The API response object
        model (str): The model name being used
        
    Returns:
        int: Delay in seconds, or None if not found
    """
    try:
        # Log analysis attempt
        logger.info("Analyzing error response to extract retry delay...")
        
        # Try to parse JSON response
        try:
            response_data = response.json()
            # Log structure for debug
            logger.debug(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            logger.warning("Non-JSON response received")
            response_data = {}
        
        # Method 1: Direct extraction via regex on raw text
        # This method is more robust if JSON structure is unexpected
        response_text = response.text
        retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', response_text)
        if retry_match:
            delay_num = int(retry_match.group(1))
            logger.info(f"Retry delay extracted via regex: {delay_num}s (+1s)")
            return delay_num + 1
            
        # Method 2: Search in nested structure (as before)
        # Possible structure 1: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"{...}","provider_name":"Google AI Studio"}}}
        if "error" in response_data and "metadata" in response_data["error"] and "raw" in response_data["error"]["metadata"]:
            raw_text = response_data["error"]["metadata"]["raw"]
            
            # Try direct extraction by regex in raw
            raw_retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', raw_text)
            if raw_retry_match:
                delay_num = int(raw_retry_match.group(1))
                logger.info(f"Retry delay extracted from 'raw' via regex: {delay_num}s (+1s)")
                return delay_num + 1
            
            # Try parsing JSON
            try:
                # Sometimes raw is a JSON string with escape characters
                # Basic cleaning before parsing
                if isinstance(raw_text, str):
                    raw_text = raw_text.replace('\\"', '"').replace('\\n', '\n')
                    
                nested_error = json.loads(raw_text)
                
                # Look for RetryInfo in details
                if "error" in nested_error and "details" in nested_error["error"]:
                    for detail in nested_error["error"]["details"]:
                        if "@type" in detail and "RetryInfo" in detail["@type"] and "retryDelay" in detail:
                            delay_str = detail["retryDelay"]
                            delay_match = re.search(r'(\d+)', delay_str)
                            if delay_match:
                                delay_num = int(delay_match.group(1))
                                logger.info(f"Retry delay extracted from 'raw' JSON: {delay_num}s (+1s)")
                                return delay_num + 1
            except Exception as e:
                logger.warning(f"Failed to parse JSON in 'raw': {e}")
                
        # No retryDelay found, return to default delay for free models
        if is_free_model(model):
            logger.info(f"No specific retry delay found. Using default delay: {30}s")
            return 30
        else:
            # For paid models, use a fixed delay of 30s as fallback
            logger.info("Paid model with no specific delay. Using standard delay of 30s.")
            return 30
        
    except Exception as e:
        logger.warning(f"Unable to extract retry delay: {e}")
        # Fallback: return 30 seconds to be safe
        return 30

def handle_api_error(response: requests.Response) -> Dict[str, Any]:
    """Gère les erreurs d'API et retourne un format standard"""
    try:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Unknown API error')
    except:
        error_message = f"HTTP Error {response.status_code}: {response.text}"
    
    logger.error(f"OpenRouter API error: {error_message}")
    return {"error": error_message}

def generate_code_with_openrouter(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 0.7,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Dict[str, Any]:
    """
    Génère du code en utilisant l'API OpenRouter.
    
    Args:
        api_key: Clé API OpenRouter
        model: Identifiant du modèle à utiliser (ex: 'anthropic/claude-3-opus:beta')
        system_prompt: Instructions système pour le modèle
        user_prompt: Description de l'application à générer
        tools: Liste des outils MCP (Model Context Protocol) à utiliser
        temperature: Température pour le contrôle de la créativité (0.0-1.0)
        max_retries: Nombre maximum de tentatives en cas d'erreur
        retry_delay: Délai en secondes entre les tentatives
    
    Returns:
        Dict contenant la réponse ou une erreur
    """
    logger.info(f"Generating code with model: {model}")
    
    # URL de l'API OpenRouter
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Construire les messages pour l'API
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Préparer les données de la requête
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    
    # Ajouter les outils MCP si fournis
    if tools:
        request_data["tools"] = tools
        request_data["tool_choice"] = "auto"
    
    # En-têtes pour l'API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://bot-project-creator.com"  # Pour le tracking OpenRouter
    }
    
    # Tenter l'appel API avec des réessais
    for attempt in range(max_retries):
        try:
            logger.info(f"API call attempt {attempt + 1}/{max_retries}")
            
            response = requests.post(
                api_url,
                headers=headers,
                json=request_data,
                timeout=180  # 3 minutes timeout for code generation
            )
            
            # Vérifier la réponse HTTP
            if response.status_code == 200:
                response_data = response.json()
                
                # Extraire le contenu de la réponse
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    # Traiter la réponse en fonction de son contenu
                    choice = response_data['choices'][0]
                    message = choice.get('message', {})
                    content = message.get('content')
                    
                    # Vérifier s'il y a des appels d'outils dans la réponse
                    tool_calls = message.get('tool_calls', [])
                    
                    # Construire la réponse
                    result = {
                        "content": content,
                        "model": response_data.get('model', model),
                        "tool_calls": tool_calls
                    }
                    
                    # Traiter ici les résultats des outils si nécessaire
                    # Dans une implémentation complète, vous exécuteriez les outils
                    # et poursuivriez la conversation avec les résultats
                    
                    logger.info(f"Code generated successfully with model {result['model']}")
                    return result
                else:
                    logger.error("Invalid API response format")
                    return {"error": "Format de réponse API invalide"}
            elif response.status_code == 429:
                # Rate limit - attendre et réessayer
                logger.warning(f"Rate limit hit. Waiting {retry_delay} seconds before retry.")
                time.sleep(retry_delay)
                continue
            else:
                # Autres erreurs HTTP
                return handle_api_error(response)
                
        except requests.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return {"error": f"Erreur de connexion à l'API OpenRouter: {str(e)}"}
    
    # Si nous arrivons ici, c'est que toutes les tentatives ont échoué
    return {"error": "Toutes les tentatives d'appel à l'API ont échoué"}


def extract_files_from_response(response_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extrait les fichiers à partir de la réponse de l'API.
    
    Args:
        response_data: Réponse complète de l'API
        
    Returns:
        Dict avec le chemin du fichier comme clé et le contenu comme valeur
    """
    files = {}
    
    # Si la réponse est vide ou ne contient pas le contenu attendu
    if not response_data or 'content' not in response_data:
        return files
    
    content = response_data.get('content', '')
    
    # Méthode 1: Recherche des blocs FILE: avec du code
    file_blocks = re.findall(r'FILE: (.+?)\n```[\w\+]*\n(.*?)```', content, re.DOTALL)
    
    # Si des blocs ont été trouvés, les ajouter au dictionnaire
    for file_path, file_content in file_blocks:
        # Normaliser le chemin du fichier
        norm_path = os.path.normpath(file_path.strip())
        files[norm_path] = file_content.strip()
    
    # Méthode 2: Recherche des blocs alternatifs (format différent)
    alt_blocks = re.findall(r'```[\w\+]*\s*(.+?)\s*```\s*(.+?)\s*```', content, re.DOTALL)
    
    # Si des blocs ont été trouvés, vérifier s'ils peuvent être des fichiers
    for potential_path, file_content in alt_blocks:
        # Vérifier si la première partie ressemble à un chemin de fichier
        if '/' in potential_path and len(potential_path.strip().split()) <= 2:  # Probablement un chemin
            norm_path = os.path.normpath(potential_path.strip())
            if norm_path not in files:  # Ne pas écraser les fichiers déjà trouvés
                files[norm_path] = file_content.strip()
    
    # Méthode 3: Recherche des marqueurs dans le texte
    lines = content.split('\n')
    current_file = None
    file_content = []
    
    for line in lines:
        # Détecter le début d'un nouveau fichier
        if line.startswith('FILE:') or (line.startswith('```') and current_file and file_content):
            # Enregistrer le fichier précédent s'il existe
            if current_file and file_content:
                file_text = '\n'.join(file_content)
                # Normaliser le chemin du fichier
                norm_path = os.path.normpath(current_file)
                # Ne pas écraser les fichiers déjà trouvés avec des méthodes précédentes
                if norm_path not in files:
                    files[norm_path] = file_text
                
                # Réinitialiser pour le prochain fichier
                current_file = None
                file_content = []
            
            # Nouveau fichier détecté
            if line.startswith('FILE:'):
                current_file = line.replace('FILE:', '').strip()
                
        # Ajouter le contenu au fichier actuel
        elif current_file and not (line.startswith('```') and len(file_content) == 0):
            # Ignorer la première ligne ``` mais pas les autres
            if not (line.startswith('```') and line.endswith('```')):
                file_content.append(line)
    
    # Traiter le dernier fichier s'il existe
    if current_file and file_content:
        file_text = '\n'.join(file_content)
        # Normaliser le chemin du fichier
        norm_path = os.path.normpath(current_file)
        # Ne pas écraser les fichiers déjà trouvés
        if norm_path not in files:
            files[norm_path] = file_text
    
    return files
