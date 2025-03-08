import logging
logger = logging.getLogger(__name__)
import json

def get_reformulated_prompt(api_client, user_prompt):
    """Use AI to reformat and structure the user's prompt"""
    reformulation_prompt = """
    You are a requirements refinement expert. Your task is to take the user's application description 
    and reformulate it into a clear, structured, and detailed specification.
    
    Format the output as a comprehensive description that covers:
    1. The main purpose of the application
    2. Key features and functionality
    3. User types/roles if applicable
    4. Data requirements and storage needs
    5. Any specific technical requirements mentioned
    
    Make sure to preserve ALL details from the original prompt but organize them better.
    Do NOT add major new features that weren't implied in the original.
    
    Return ONLY the reformulated description, without any explanations or metadata.
    """
    
    try:
        response = api_client.call_agent(reformulation_prompt, user_prompt, max_tokens=1000)
        logger.info(f"API response received, length: {len(response) if response else 0}")
        return response.strip() if response else user_prompt
    except Exception as e:
        logger.error(f"Error reformulating prompt: {str(e)}")
        return user_prompt
