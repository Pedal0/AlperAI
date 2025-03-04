import json
import openai
import time
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAppGeneratorAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        self.model = "gpt-4o-mini"
        self.temperature = 0.2
        self.max_retries = 3
        self.retry_delay = 2 
        
    def call_agent(self, prompt: str, user_input: str, max_tokens: int = 2000) -> Optional[str]:
        """Call the OpenAI API with retry mechanism and better error handling"""
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
                    wait_time = self.retry_delay * (2 ** (attempts - 1))  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached, giving up")
                    return None
    
    def _safe_parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON with detailed error reporting"""
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
                    
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response (first 500 chars): {json_str[:500]}")
            return None
    
    def analyze_requirements(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        from config import REQUIREMENTS_ANALYZER_PROMPT
        
        response = self.call_agent(REQUIREMENTS_ANALYZER_PROMPT, user_prompt, max_tokens=2000)
        return self._safe_parse_json(response)
    
    def design_architecture(self, requirements_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from config import ARCHITECTURE_DESIGNER_PROMPT
        
        req_json = json.dumps(requirements_spec, indent=2)
        
        response = self.call_agent(ARCHITECTURE_DESIGNER_PROMPT, req_json, max_tokens=4000)
        
        architecture = self._safe_parse_json(response)
        
        if architecture:
            logger.info("Architecture design successful")
        else:
            logger.error("Architecture design failed")
            
        return architecture
    
    def design_database(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from config import DATABASE_DESIGNER_PROMPT
        
        context = {
            "requirements": requirements_spec,
            "architecture": architecture
        }
        
        response = self.call_agent(DATABASE_DESIGNER_PROMPT, json.dumps(context), max_tokens=3000)
        return self._safe_parse_json(response)
    
    def design_api(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from config import API_DESIGNER_PROMPT
        
        context = {
            "requirements": requirements_spec,
            "architecture": architecture
        }
        
        response = self.call_agent(API_DESIGNER_PROMPT, json.dumps(context), max_tokens=3000)
        return self._safe_parse_json(response)
    
    def generate_code(self, file_spec: Dict[str, Any], project_context: Dict[str, Any]) -> Optional[str]:
        from config import CODE_GENERATOR_PROMPT
        
        context = {
            "file_specification": file_spec,
            "project_context": project_context
        }
        
        return self.call_agent(CODE_GENERATOR_PROMPT, json.dumps(context), max_tokens=4000)
    
    def test_generator(self, file_path: str, code_content: str, project_context: Dict[str, Any]) -> Optional[str]:
        from config import TEST_GENERATOR_PROMPT
        
        context = {
            "file_path": file_path,
            "code_content": code_content,
            "project_context": project_context
        }
        
        return self.call_agent(TEST_GENERATOR_PROMPT, json.dumps(context), max_tokens=3000)
    
    def code_reviewer(self, file_path: str, code_content: str, file_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from config import CODE_REVIEWER_PROMPT
        
        context = {
            "file_path": file_path,
            "code_content": code_content,
            "file_specification": file_spec
        }
        
        response = self.call_agent(CODE_REVIEWER_PROMPT, json.dumps(context), max_tokens=2000)
        return self._safe_parse_json(response)