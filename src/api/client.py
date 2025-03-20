import json
import openai
import time
import logging
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from src.config import (
    REQUIREMENTS_ANALYZER_PROMPT,
    ARCHITECTURE_DESIGNER_PROMPT,
    DATABASE_DESIGNER_PROMPT,
    API_DESIGNER_PROMPT,
    CODE_GENERATOR_PROMPT,
    TEST_GENERATOR_PROMPT,
    CODE_REVIEWER_PROMPT,
    FILE_SIGNATURE_EXTRACTOR_PROMPT,
    CROSS_FILE_REVIEWER_PROMPT,
    API_MODEL,
    API_TEMPERATURE,
    MAX_TOKENS_DEFAULT,
    MAX_TOKENS_LARGE,
    MAX_TOKENS_HUGE,
    PROJECT_FILES_GENERATOR_PROMPT,
    USE_OPENROUTER,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    TEMPERATURES
)
from src.api.agent_calls.requirements import analyze_requirements
from src.api.agent_calls.architecture import design_architecture
from src.api.agent_calls.database import design_database
from src.api.agent_calls.api_design import design_api
from src.api.agent_calls.code_generation import generate_code, generate_project_file
from src.api.agent_calls.code_review import extract_file_signature, review_code, cross_file_review

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAppGeneratorAPI:
    def __init__(self, api_key: str = None):
        # Load environment variables
        load_dotenv()
        
        # Get API keys from environment variables if not provided
        self.openai_api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        
        if not self.openai_api_key and not self.openrouter_api_key:
            logger.error("No API keys found in .env file or provided as argument")
            raise ValueError("No API keys found. Please add OPENAI_API_KEY or OPENROUTER_API_KEY to your .env file")
        
        # If OpenRouter is enabled but no key is available, use OpenAI
        if USE_OPENROUTER and not self.openrouter_api_key:
            logger.warning("OpenRouter is enabled but no OPENROUTER_API_KEY found. Falling back to OpenAI.")
            
        self.openai_client = None
        self.setup_client()
        self.model = OPENROUTER_MODEL if USE_OPENROUTER and self.openrouter_api_key else API_MODEL
        self.temperature = TEMPERATURES["default"]
        self.max_retries = 3
        self.retry_delay = 2
        
    def setup_client(self):
        """Set up the OpenAI client based on configuration"""
        if USE_OPENROUTER and self.openrouter_api_key:
            self.openai_client = openai.OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.openrouter_api_key,
            )
            logger.info(f"Using OpenRouter with model: {OPENROUTER_MODEL}")
        else:
            openai.api_key = self.openai_api_key
            self.openai_client = None
            logger.info(f"Using OpenAI with model: {API_MODEL}")
        
    def call_agent(self, prompt: str, user_input: str, max_tokens: int = MAX_TOKENS_DEFAULT, agent_type: str = "default") -> Optional[str]:
        attempts = 0
        
        # Get appropriate temperature for this agent type
        temperature = TEMPERATURES.get(agent_type, TEMPERATURES["default"])
        
        while attempts < self.max_retries:
            try:
                logger.info(f"Making API call (attempt {attempts + 1}/{self.max_retries}) with temperature {temperature}")
                
                if USE_OPENROUTER and self.openrouter_api_key and agent_type != "agent_team":
                    # Ensure client is properly initialized
                    if not self.openai_client:
                        self.setup_client()
                        
                    response = self.openai_client.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_input}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                else:
                    # Use standard OpenAI for agent team or when OpenRouter is not configured
                    if not self.openai_api_key:
                        logger.error("No OpenAI API key available for this call")
                        return None
                        
                    model_to_use = API_MODEL
                    response = openai.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_input}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                
                content = response.choices[0].message.content
                logger.info(f"API call successful, received {len(content)} characters")
                return content
            except Exception as e:
                attempts += 1
                logger.error(f"API call error: {e}")
                if attempts < self.max_retries:
                    wait_time = self.retry_delay * (2 ** (attempts - 1))  
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached, giving up")
                    return None
    
    def _safe_parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        if not json_str:
            logger.error("Empty response received")
            return None
            
        try:
            if "```json" in json_str or "```" in json_str:
                start = json_str.find("```json")
                if start != -1:
                    start += 7  
                else:
                    start = json_str.find("```")
                    if start != -1:
                        start += 3  
                
                if start != -1:
                    end = json_str.find("```", start)
                    if end != -1:
                        json_str = json_str[start:end].strip()
                    
            parsed_result = json.loads(json_str)
            
            if not isinstance(parsed_result, dict):
                logger.error(f"JSON parsed but result is not a dictionary: {type(parsed_result)}")
                logger.error(f"First 500 chars of result: {str(parsed_result)[:500]}")
                return {}
                
            return parsed_result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response (first 500 chars): {json_str[:500]}")
            return None
    
    # Delegate to specialized modules
    def analyze_requirements(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        return analyze_requirements(self, user_prompt)
    
    def design_architecture(self, requirements_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return design_architecture(self, requirements_spec)
    
    def design_database(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return design_database(self, requirements_spec, architecture)
    
    def design_api(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return design_api(self, requirements_spec, architecture)
    
    def generate_code(self, file_spec: Dict[str, Any], project_context: Dict[str, Any]) -> Optional[str]:
        return generate_code(self, file_spec, project_context)
    
    def test_generator(self, file_path: str, code_content: str, project_context: Dict[str, Any]) -> Optional[str]:
        from src.api.agent_calls.test_generation import generate_tests
        return generate_tests(self, file_path, code_content, project_context)
    
    def code_reviewer(self, file_path: str, code_content: str, file_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return review_code(self, file_path, code_content, file_spec)
    
    def extract_file_signature(self, file_path: str, content: str) -> Dict[str, Any]:
        return extract_file_signature(self, file_path, content)
    
    def cross_file_code_reviewer(self, all_files: Dict[str, str], project_context: Dict[str, Any]) -> Dict[str, str]:
        return cross_file_review(self, all_files, project_context)
    
    def generate_project_file(self, file_type: str, project_context: Dict[str, Any], file_structure: List[str]) -> str:
        return generate_project_file(self, file_type, project_context, file_structure)
