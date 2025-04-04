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
        "User-Agent": "CodeGenApp/1.0" # Good practice to identify your app
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream
    }
    response = None # Initialize response to None
    
    for retry_attempt in range(max_retries + 1):  # +1 to include initial attempt
        try:
            # Indicate attempt number if not the first one
            if retry_attempt > 0:
                st.info(f"🔄 Attempt #{retry_attempt+1}/{max_retries+1} calling API...")
                
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=300) # Long timeout
            
            # If no HTTP error, return JSON response
            if response.status_code == 200:
                if retry_attempt > 0:
                    st.success(f"✅ Success after {retry_attempt+1} attempts!")
                return response.json()
            
            # If error 429 (Rate Limit), try to extract retryDelay
            elif response.status_code == 429:
                # Show error and response for debug
                st.error(f"Error 429 (Rate Limit) on attempt #{retry_attempt+1}")
                
                retry_delay = extract_retry_delay(response, model) 
                
                if retry_delay and retry_attempt < max_retries:
                    st.warning(f"⚠️ Error 429 (Rate Limit). Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                    continue  # Try again after delay
                else:
                    if retry_attempt >= max_retries:
                        st.error(f"❌ Maximum number of attempts reached ({max_retries+1})")
                    else:
                        st.error("❌ No retry delay found in response")
                    # No retryDelay found or no more attempts possible
                    response.raise_for_status()  # Will trigger HTTPError exception
            else:
                # Other HTTP error codes
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            st.error("Error: API request timeout exceeded (300 seconds). Generation might be too long.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"Error during OpenRouter API call: {e}")
            if response is not None:
                try:
                    st.error(f"API response (status {response.status_code}): {response.text}")
                except Exception: # In case response.text isn't readable
                     st.error(f"API response (status {response.status_code}) not decodable.")
            return None
        except json.JSONDecodeError:
            st.error(f"Error: Unable to decode JSON response from API.")
            if response is not None:
               st.error(f"Raw response received: {response.text}")
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
        # Show raw response for debug
        st.info("Analyzing error response to extract retry delay...")
        
        # Try to parse JSON response
        try:
            response_data = response.json()
            # Show structure for debug
            st.code(json.dumps(response_data, indent=2), language="json")
        except json.JSONDecodeError:
            st.warning("Non-JSON response received")
            response_data = {}
        
        # Method 1: Direct extraction via regex on raw text
        # This method is more robust if JSON structure is unexpected
        response_text = response.text
        retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', response_text)
        if retry_match:
            delay_num = int(retry_match.group(1))
            st.success(f"✅ Retry delay extracted via regex: {delay_num}s (+1s)")
            return delay_num + 1
            
        # Method 2: Search in nested structure (as before)
        # Possible structure 1: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"{...}","provider_name":"Google AI Studio"}}}
        if "error" in response_data and "metadata" in response_data["error"] and "raw" in response_data["error"]["metadata"]:
            raw_text = response_data["error"]["metadata"]["raw"]
            
            # Try direct extraction by regex in raw
            raw_retry_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', raw_text)
            if raw_retry_match:
                delay_num = int(raw_retry_match.group(1))
                st.success(f"✅ Retry delay extracted from 'raw' via regex: {delay_num}s (+1s)")
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
                                st.success(f"✅ Retry delay extracted from 'raw' JSON: {delay_num}s (+1s)")
                                return delay_num + 1
            except Exception as e:
                st.warning(f"Failed to parse JSON in 'raw': {e}")
                
        # No retryDelay found, return to default delay for free models
        if is_free_model(model):
            st.info(f"No specific retry delay found. Using default delay: {30}s")
            return 30
        else:
            # For paid models, use a fixed delay of 30s as fallback
            st.info("Paid model with no specific delay. Using standard delay of 30s.")
            return 30
        
    except Exception as e:
        st.warning(f"Unable to extract retry delay: {e}")
        # Fallback: return 30 seconds to be safe
        return 30
