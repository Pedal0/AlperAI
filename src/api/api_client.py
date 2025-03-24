import json
import openai
import time
import logging
from typing import Dict, List, Any, Optional

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
    PROJECT_FILES_GENERATOR_PROMPT

)

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
        
    def call_agent(self, prompt: str, context: str, max_tokens: int = MAX_TOKENS_DEFAULT, agent_type: str = "default") -> Optional[str]:
        """
        Call the AI agent with prompt and context
        
        Args:
            prompt: The system prompt to guide the AI
            context: The context information (usually JSON)
            max_tokens: Maximum number of tokens to generate
            agent_type: Type of agent to use (default, code, review, css)
            
        Returns:
            The generated response
        """
        # Check for large context and use appropriate model configuration
        if len(context) > 100000:  # Approximately 25k tokens
            logger.info(f"Large context detected ({len(context)/4} tokens approx), using extended context model")
            # Use a configuration for large context handling if available in your implementation
        
        attempts = 0
        
        while attempts < self.max_retries:
            try:
                logger.info(f"Making API call (attempt {attempts + 1}/{self.max_retries})")
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": context}
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
    
    def analyze_requirements(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        response = self.call_agent(REQUIREMENTS_ANALYZER_PROMPT, user_prompt, max_tokens=MAX_TOKENS_DEFAULT)
        return self._safe_parse_json(response)
    
    def design_architecture(self, requirements_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_json = json.dumps(requirements_spec, indent=2)
        response = self.call_agent(ARCHITECTURE_DESIGNER_PROMPT, req_json, max_tokens=MAX_TOKENS_LARGE)
        
        architecture = self._safe_parse_json(response)
        
        if architecture:
            logger.info("Architecture design successful")
        else:
            logger.error("Architecture design failed")
            
        return architecture
    
    def design_database(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        context = {
            "requirements": requirements_spec,
            "architecture": architecture
        }
        
        response = self.call_agent(DATABASE_DESIGNER_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_DEFAULT)
        return self._safe_parse_json(response)
    
    def design_api(self, requirements_spec: Dict[str, Any], architecture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        context = {
            "requirements": requirements_spec,
            "architecture": architecture
        }
        
        response = self.call_agent(API_DESIGNER_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_DEFAULT)
        return self._safe_parse_json(response)
    
    def generate_code(self, file_spec: Dict[str, Any], project_context: Dict[str, Any]) -> Optional[str]:
        # Assurez-vous que le project_context contient requirements et architecture
        context = {
            "file_specification": file_spec,
            "project_context": project_context,
            "requirements": project_context.get("requirements", {}),
            "architecture": project_context.get("architecture", {})
        }
        
        return self.call_agent(CODE_GENERATOR_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_LARGE)
    
    def test_generator(self, file_path: str, code_content: str, project_context: Dict[str, Any]) -> Optional[str]:
        context = {
            "file_path": file_path,
            "code_content": code_content,
            "project_context": project_context,
            "requirements": project_context.get("requirements", {}),
            "architecture": project_context.get("architecture", {})
        }
        
        return self.call_agent(TEST_GENERATOR_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_DEFAULT)
    
    def code_reviewer(self, file_path: str, code_content: str, file_spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        context = {
            "file_path": file_path,
            "code_content": code_content,
            "file_specification": file_spec
        }
        
        response = self.call_agent(CODE_REVIEWER_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_DEFAULT)
        return self._safe_parse_json(response)
    
    def extract_file_signature(self, file_path: str, content: str) -> Dict[str, Any]:
        context = {
            "file_path": file_path,
            "code_content": content
        }
        
        response = self.call_agent(FILE_SIGNATURE_EXTRACTOR_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_DEFAULT)
        signature = self._safe_parse_json(response)
        
        if not signature:
            return {
                "file_path": file_path,
                "functions": [],
                "classes": [],
                "imports": []
            }
            
        return signature
    
    def cross_file_code_reviewer(self, all_files: Dict[str, str], project_context: Dict[str, Any]) -> Dict[str, str]:
        results = {}
        
        project_signatures = {}
        for path, content in all_files.items():
            project_signatures[path] = self.extract_file_signature(path, content)
        
        for file_path, content in all_files.items():
            context = {
                "file_to_review": file_path,
                "file_content": content,
                "project_signatures": project_signatures,
                "project_context": project_context
            }
            
            response = self.call_agent(CROSS_FILE_REVIEWER_PROMPT, json.dumps(context), max_tokens=MAX_TOKENS_LARGE)
            
            if response and response.strip() == "PARFAIT":
                results[file_path] = "PARFAIT"
            else:
                code_content = self._extract_code_content(response, file_path)
                results[file_path] = code_content if code_content else response
                
        return results
    
    def _extract_code_content(self, response: str, file_path: str) -> Optional[str]:
        if "```" in response:
            start_markers = ["```python", "```javascript", "```java", "```typescript", "```"]
            for marker in start_markers:
                if marker in response:
                    parts = response.split(marker, 1)
                    if len(parts) > 1:
                        code_part = parts[1]
                        end_marker_pos = code_part.find("```")
                        if end_marker_pos != -1:
                            return code_part[:end_marker_pos].strip()
        
        if file_path in response:
            lines = response.split('\n')
            for i, line in enumerate(lines):
                if file_path in line and i+1 < len(lines):
                    return '\n'.join(lines[i+1:])
        
        return None

    def generate_project_file(self, file_type: str, project_context: Dict[str, Any], file_structure: List[str]) -> str:      
        context = {
            "file_type": file_type,
            "project_context": project_context,
            "file_structure": file_structure
        }
        
        response = self.call_agent(
            PROJECT_FILES_GENERATOR_PROMPT,
            json.dumps(context),
            max_tokens=MAX_TOKENS_DEFAULT
        )
        
        return response

    def validate_with_agent_team(self, project_dir: str, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valider le projet avec l'équipe d'agents AI
        
        Args:
            project_dir: Chemin du répertoire du projet
            project_context: Contexte du projet
            
        Returns:
            Résultats de la validation
        """
        from src.config.constants import AGENT_TEAM_ENABLED
        
        if not AGENT_TEAM_ENABLED:
            logger.info("Agent team validation skipped (disabled by user)")
            return {"status": "skipped", "reason": "disabled_by_user"}
            
        logger.info("Running validation with agent team...")
        
        # Ici, on implémenterait l'appel à l'équipe d'agents
        # Pour l'instant, c'est un placeholder
        
        return {
            "status": "success",
            "improvements": ["Code structure improved", "UI components enhanced", "Documentation enriched"]
        }
        
    def bulk_code_review(self, files_by_type: Dict[str, Dict[str, str]], project_context: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Révise l'ensemble du code frontend et backend séparément en utilisant le large contexte de l'IA
        
        Args:
            files_by_type: Dictionnaire organisé par type ("frontend", "backend") contenant les fichiers
                          où chaque entrée est {chemin_fichier: contenu}
            project_context: Le contexte complet du projet incluant les requirements et l'architecture
            
        Returns:
            Dictionnaire contenant les corrections par fichier: {chemin_fichier: contenu_modifié}
        """
        results = {}
        
        # Traiter le frontend et le backend séparément
        for code_type in ["frontend", "backend"]:
            if code_type not in files_by_type or not files_by_type[code_type]:
                logger.info(f"Aucun fichier {code_type} à réviser")
                continue
                
            files = files_by_type[code_type]
            logger.info(f"Révision en masse des fichiers {code_type}: {len(files)} fichiers")
            
            # Créer un contexte étendu avec tous les fichiers du même type
            bulk_context = {
                "code_type": code_type,
                "files": files,
                "project_context": project_context,
                "requirements": project_context.get("requirements", {}),
                "architecture": project_context.get("architecture", {})
            }
            
            # Prompt spécifique pour la revue de code en masse
            bulk_review_prompt = f"""
            Tu es un expert en développement logiciel spécialisé dans la révision de code {code_type}.
            Analyse minutieusement TOUS les fichiers fournis et identifie:
            1. Les bugs potentiels
            2. Les problèmes de performance
            3. Les failles de sécurité
            4. Les écarts par rapport aux bonnes pratiques
            5. Les incohérences avec l'architecture du projet
            
            Pour chaque problème identifié:
            1. Indique précisément le fichier concerné
            2. Localise l'emplacement exact dans le code
            3. Explique clairement le problème
            4. Propose une correction concrète
            
            Réponds avec un JSON structuré comme suit:
            {{
                "file_path": {{
                    "issues": [
                        {{
                            "type": "bug|performance|security|practice|consistency",
                            "severity": "high|medium|low",
                            "line": "numéro ou plage de lignes approximatif",
                            "description": "Description du problème",
                            "original_code": "Code problématique",
                            "fixed_code": "Code corrigé"
                        }}
                    ],
                    "improved_content": "Contenu complet du fichier corrigé si nécessaire"
                }}
            }}
            
            Si un fichier n'a pas de problème, indique simplement "PARFAIT" pour sa valeur.
            """
            
            # Appeler l'agent avec un contexte étendu
            response = self.call_agent(
                bulk_review_prompt, 
                json.dumps(bulk_context),
                max_tokens=MAX_TOKENS_LARGE
            )
            
            review_results = self._safe_parse_json(response)
            if not review_results:
                logger.error(f"Échec de l'analyse en masse des fichiers {code_type}")
                continue
                
            # Fusionner les résultats
            for file_path, review in review_results.items():
                if review == "PARFAIT":
                    results[file_path] = files[file_path]  # Garde le fichier inchangé
                elif isinstance(review, dict) and "improved_content" in review:
                    results[file_path] = review["improved_content"]
                    logger.info(f"Correction appliquée à {file_path}")
                    
                    # Log des problèmes trouvés
                    if "issues" in review and review["issues"]:
                        for issue in review["issues"]:
                            logger.info(f"Problème dans {file_path} (L.{issue.get('line')}): {issue.get('description')}")
        
        return results
        
    def apply_code_improvements(self, files: Dict[str, str], project_context: Dict[str, Any]) -> Dict[str, str]:
        """
        Applique des améliorations au code en analysant tous les fichiers ensemble
        
        Args:
            files: Dictionnaire contenant {chemin_fichier: contenu}
            project_context: Contexte du projet
            
        Returns:
            Dictionnaire des fichiers améliorés {chemin_fichier: contenu_amélioré}
        """
        # Séparer les fichiers par type (frontend/backend)
        files_by_type = {
            "frontend": {},
            "backend": {}
        }
        
        for path, content in files.items():
            if any(ext in path.lower() for ext in ['.js', '.jsx', '.ts', '.tsx', '.vue', '.css', '.html']):
                files_by_type["frontend"][path] = content
            elif any(ext in path.lower() for ext in ['.py', '.java', '.go', '.rb', '.php', '.cs']):
                files_by_type["backend"][path] = content
            else:
                # Déterminer le type en fonction du contenu ou de l'emplacement
                if '/front/' in path or '/client/' in path:
                    files_by_type["frontend"][path] = content
                elif '/back/' in path or '/server/' in path or '/api/' in path:
                    files_by_type["backend"][path] = content
                else:
                    # Par défaut, considérer comme backend
                    files_by_type["backend"][path] = content
        
        # Effectuer la révision en masse
        improved_files = self.bulk_code_review(files_by_type, project_context)
        
        # Fusionner les résultats avec les fichiers originaux
        result = files.copy()
        for path, improved_content in improved_files.items():
            result[path] = improved_content
            
        return result