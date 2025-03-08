import json
import openai
import time
import logging
from typing import Dict, List, Any, Optional

from src.config import (
    API_MODEL,
    API_TEMPERATURE,
    MAX_TOKENS_DEFAULT,
    MAX_TOKENS_LARGE
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
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        self.model = API_MODEL
        self.temperature = API_TEMPERATURE
        self.max_retries = 3
        self.retry_delay = 2 
        
    def call_agent(self, prompt: str, user_input: str, max_tokens: int = MAX_TOKENS_DEFAULT) -> Optional[str]:
        attempts = 0
        
        while attempts < self.max_retries:
            try:
                logger.info(f"Making API call (attempt {attempts + 1}/{self.max_retries})")
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=self.temperature,
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
