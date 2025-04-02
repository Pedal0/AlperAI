"""
OpenRouter API integration module.
Handles all communication with the OpenRouter API.
"""
import re
import json
import time
import requests
import streamlit as st
from src.config.constants import OPENROUTER_API_URL
from src.utils.model_utils import is_free_model

def call_openrouter_api(api_key, model, messages, temperature=0.7, stream=False, max_retries=1):
    """
    Call the OpenRouter API and handle basic errors.
    
    Args:
        api_key (str): OpenRouter API key
        model (str): Model name to use
        messages (list): List of message objects
        temperature (float): Temperature parameter for generation
        stream (bool): Whether to stream the response
        max_retries (int): Maximum number of retries on failure
        
    Returns:
        dict: JSON response or None on error
    """
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
    """
    Extract the retryDelay from a 429 error response.
    
    Args:
        response (Response): The API response object
        model (str): The model name being used
        
    Returns:
        int: Delay in seconds, or None if not found
    """
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
            st.info(f"Aucun délai de retry spécifique trouvé. Utilisation du délai par défaut: {30}s")
            return 30
        else:
            # Pour les modèles payants, utiliser un délai fixe de 30s comme fallback
            st.info("Modèle payant sans délai spécifié. Utilisation d'un délai standard de 30s.")
            return 30
        
    except Exception as e:
        st.warning(f"Impossible d'extraire le délai de retry: {e}")
        # Fallback: retourner 30 secondes pour être sûr
        return 30
