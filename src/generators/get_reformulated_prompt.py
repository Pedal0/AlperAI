import logging
logger = logging.getLogger(__name__)
import json
from src.config import (
    REFORMULATION_PROMPT,
)

def get_reformulated_prompt(api_client, user_prompt):
    """
    Use AI to reformat and structure the user's prompt into a comprehensive
    specification with detailed sections for frontend, backend, and database components.
    """    
    try:           
        logger.info("Reformulating user prompt into structured specification...")
        
        response = api_client.call_agent(
            REFORMULATION_PROMPT, 
            user_prompt, 
            max_tokens=20000,  # Increased token limit for more detailed output
            agent_type="reformulation"
        )
        
        logger.info(f"Structured specification received, length: {len(response) if response else 0}")
        
        # Preserve special project markers if they were in the original prompt
        if response and "[COMPLETE PROJECT WITH ALL FILES]" in user_prompt and "[COMPLETE PROJECT WITH ALL FILES]" not in response:
            response = "[COMPLETE PROJECT WITH ALL FILES] " + response
            
        return response.strip() if response else user_prompt
    except Exception as e:
        logger.error(f"Error reformulating prompt: {str(e)}")
        return user_prompt
