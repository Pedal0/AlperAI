"""
Client MCP pour le serveur codebase-mcp de DeDeveloper23.
Permet d'analyser automatiquement les codebases générées pour validation et correction.
"""

import json
import subprocess
import tempfile
import os
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any

class CodebaseMCPClient:
    """
    Client pour interagir avec le serveur codebase-mcp.
    """
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize the codebase MCP client.
        
        Args:
            api_key (str): OpenRouter API key for AI analysis
            model (str): Model to use for code analysis
        """
        self.api_key = api_key
        self.model = model
        self.server_process = None
        
    @contextmanager
    def codebase_server(self, target_directory: str):
        """
        Context manager pour démarrer et arrêter le serveur codebase-mcp.
        
        Args:
            target_directory (str): Répertoire du projet à analyser
        """
        server_process = None
        try:
            # Changer vers le répertoire cible
            original_cwd = os.getcwd()
            os.chdir(target_directory)
            
            # Démarrer le serveur codebase-mcp
            logging.info(f"Starting codebase-mcp server in {target_directory}")
            server_process = subprocess.Popen(
                ["codebase-mcp", "start"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=target_directory
            )
            
            yield server_process
            
        except Exception as e:
            logging.error(f"Error with codebase-mcp server: {e}")
            raise
        finally:
            # Nettoyer
            if server_process:
                try:
                    server_process.terminate()
                    server_process.wait(timeout=5)
                except:
                    try:
                        server_process.kill()
                    except:
                        pass
            
            # Restaurer le répertoire de travail
            try:
                os.chdir(original_cwd)
            except:
                pass
    
    async def get_codebase_analysis(self, target_directory: str, format_type: str = "xml") -> str:
        """
        Obtient une analyse complète de la codebase via le serveur MCP.
        
        Args:
            target_directory (str): Répertoire du projet à analyser
            format_type (str): Format de sortie ('xml', 'markdown', 'plain')
            
        Returns:
            str: Analyse complète de la codebase
        """
        try:
            # Utiliser le serveur codebase-mcp pour analyser le projet
            with self.codebase_server(target_directory) as server:
                # Simuler l'appel MCP getCodebase
                result = await self._call_mcp_tool(
                    server,
                    "getCodebase",
                    {
                        "cwd": target_directory,
                        "format": format_type,
                        "includeFileSummary": True,
                        "includeDirectoryStructure": True,
                        "showLineNumbers": True,
                        "removeComments": False,
                        "removeEmptyLines": False
                    }
                )
                
                return result
                
        except Exception as e:
            logging.error(f"Error getting codebase analysis: {e}")
            # Fallback vers la méthode directe si le serveur MCP échoue
            return await self._fallback_direct_analysis(target_directory)
    
    async def _call_mcp_tool(self, server_process, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Appelle un outil MCP via le serveur.
        
        Args:
            server_process: Processus du serveur MCP
            tool_name (str): Nom de l'outil à appeler
            args (Dict): Arguments pour l'outil
            
        Returns:
            str: Résultat de l'outil
        """
        # Construction de la requête MCP
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        # Envoyer la requête au serveur
        request_json = json.dumps(request)
        server_process.stdin.write(request_json + "\n")
        server_process.stdin.flush()
        
        # Lire la réponse
        response_line = server_process.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            if "result" in response:
                # Extraire le contenu de la réponse MCP
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")
        
        return ""
    
    async def _fallback_direct_analysis(self, target_directory: str) -> str:
        """
        Méthode de secours : analyse directe des fichiers si MCP échoue.
        
        Args:
            target_directory (str): Répertoire à analyser
            
        Returns:
            str: Analyse des fichiers
        """
        try:
            # Utiliser RepoMix directement si disponible
            result = subprocess.run(
                ["npx", "repomix", target_directory, "--output-format", "xml"],
                capture_output=True,
                text=True,
                cwd=target_directory
            )
            
            if result.returncode == 0:
                return result.stdout
                
        except Exception as e:
            logging.warning(f"RepoMix fallback failed: {e}")
        
        # Dernière option : lecture directe des fichiers
        return self._read_files_directly(target_directory)
    
    def _read_files_directly(self, target_directory: str) -> str:
        """
        Lecture directe des fichiers comme méthode de secours finale.
        
        Args:
            target_directory (str): Répertoire à analyser
            
        Returns:
            str: Contenu des fichiers
        """
        target_path = Path(target_directory)
        file_contents = ""
        
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml'}
        
        for file_path in target_path.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in code_extensions and
                file_path.stat().st_size < 100000):
                
                # Skip common ignore patterns
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if any(part in ['node_modules', '__pycache__', '.git', 'venv', 'env'] for part in file_path.parts):
                    continue
                
                try:
                    relative_path = file_path.relative_to(target_path)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        file_contents += f"\n\n=== FILE: {relative_path} ===\n{content}"
                except Exception as e:
                    logging.warning(f"Could not read file {file_path}: {e}")
        
        return file_contents
    
    async def analyze_and_validate_project(self, target_directory: str, user_prompt: str, reformulated_prompt: str) -> Dict[str, Any]:
        """
        Analyse complète du projet avec validation et suggestions de corrections.
        
        Args:
            target_directory (str): Répertoire du projet
            user_prompt (str): Demande originale de l'utilisateur
            reformulated_prompt (str): Demande reformulée
            
        Returns:
            Dict: Résultats d'analyse avec corrections suggérées
        """
        from src.api.openrouter_api import call_openrouter_api
        
        # Obtenir l'analyse complète de la codebase
        codebase_analysis = await self.get_codebase_analysis(target_directory, "xml")
        
        # Prompt d'analyse utilisant l'analyse RepoMix
        analysis_prompt = f"""ANALYSE AVANCÉE DE CODEBASE AVEC REPOMIX

CONTEXTE DU PROJET:
- Répertoire: {target_directory}
- Demande utilisateur: {user_prompt}
- Exigences reformulées: {reformulated_prompt}

ANALYSE REPOMIX COMPLÈTE:
{codebase_analysis[:20000]}{"..." if len(codebase_analysis) > 20000 else ""}

VOTRE MISSION:
Effectuez une analyse approfondie de cette codebase générée automatiquement et identifiez TOUS les problèmes à corriger.

CHECKLIST D'ANALYSE CRITIQUE:
🔍 STRUCTURE: Architecture, organisation des fichiers, nommage
🔍 SYNTAXE: Erreurs Python, JavaScript, TypeScript, HTML, CSS
🔍 IMPORTS: Déclarations manquantes, imports inutiles, chemins incorrects
🔍 DÉPENDANCES: package.json, requirements.txt, versions compatibles
🔍 API: Cohérence frontend-backend, routes, paramètres, formats
🔍 BASE DE DONNÉES: Modèles, migrations, connexions
🔍 CONFIGURATION: Variables d'environnement, fichiers config
🔍 SÉCURITÉ: Vulnérabilités évidentes, validation des données
🔍 PERFORMANCE: Goulots d'étranglement, optimisations
🔍 TESTS: Couverture, qualité des tests
🔍 FONCTIONNALITÉ: Logique métier, flux de données

FORMAT DE RÉPONSE:
Si des problèmes sont trouvés:
"🔧 PROBLÈMES DÉTECTÉS:

CRITIQUES (cassent l'application):
1. [Description détaillée] dans [fichier:ligne] - Solution: [correction spécifique]

IMPORTANTS (dégradent l'expérience):
2. [Description détaillée] dans [fichier:ligne] - Solution: [correction spécifique]

MINEURS (bonnes pratiques):
3. [Description détaillée] dans [fichier:ligne] - Solution: [correction spécifique]

AMÉLIORATIONS SUGGÉRÉES:
- [Suggestion d'amélioration avec justification]"

Si aucun problème:
"✅ CODEBASE VALIDÉE - Aucun problème détecté"

IMPORTANT: Soyez exhaustif et précis. Cette analyse sera utilisée pour des corrections automatiques."""

        # Appel à l'IA pour l'analyse
        messages = [
            {
                "role": "system", 
                "content": "Vous êtes un expert en analyse de code et architecture logicielle. Utilisez l'analyse RepoMix fournie pour effectuer une validation complète et approfondie."
            },
            {"role": "user", "content": analysis_prompt}
        ]
        
        response = call_openrouter_api(self.api_key, self.model, messages, temperature=0.2, max_retries=2)
        
        analysis_result = {
            "success": False,
            "analysis": "",
            "has_issues": False,
            "codebase_context": codebase_analysis[:10000]  # Garder un extrait pour référence
        }
        
        if response and response.get("choices"):
            analysis_text = response["choices"][0]["message"]["content"]
            analysis_result.update({
                "success": True,
                "analysis": analysis_text,
                "has_issues": "🔧" in analysis_text or "PROBLÈMES DÉTECTÉS" in analysis_text.upper()
            })
        
        return analysis_result