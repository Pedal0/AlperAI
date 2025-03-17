import logging
import time
import os
from typing import Dict, Any
from src.config import AGENT_TEAM_ENABLED, AGENT_TEAM_WAIT_TIME
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.file import FileTools
from agno.tools.duckduckgo import DuckDuckGoTools
from pathlib import Path

logger = logging.getLogger(__name__)

# Flag to ensure the verification team is launched only once
_verification_team_launched = False

def run_verification_team(app_path: str, project_context: Dict[str, Any]) -> bool:
    """
    Lance l'équipe d'agents pour vérifier et corriger le projet.
    Cette fonction retourne True quand l'équipe est lancée, pour indiquer 
    qu'aucune validation supplémentaire n'est nécessaire.
    L'équipe n'est lancée qu'une seule fois pendant l'exécution du programme.
    
    Args:
        app_path: Chemin du projet généré
        project_context: Contexte du projet (requirements, architecture, etc.)
        
    Returns:
        bool: True si l'équipe d'agents a été lancée et qu'aucune validation supplémentaire n'est nécessaire
    """
    global _verification_team_launched
    
    if _verification_team_launched:
        logger.info("Agent team has already been launched, ignoring this new request")
        return True
        
    if not AGENT_TEAM_ENABLED:
        logger.info("Agent verification team is disabled")
        return False
    
    logger.info(f"Launching agent team to verify the project at {app_path}")
    
    try:
        # Utilisation du chemin fourni par l'utilisateur
        abs_path = os.path.abspath(app_path)
        logger.info(f"Agents are working on absolute path: {abs_path}")
        
        # Création des outils pour la manipulation des fichiers
        file_tools = FileTools(Path(abs_path), True, True, True)

        # Création de l'agent spécialisé dans le développement frontend
        frontend_developer = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Frontend_Developer",
            tools=[file_tools, DuckDuckGoTools()],
            instructions=[
            """
            You are an agent equipped with tools to read, write and browse files and web search.
            You specialize in VERIFYING and IMPROVING frontend code of an existing project.
            
            IMPORTANT INSTRUCTIONS:
            - ANALYZE EXHAUSTIVELY ALL frontend files in the project
            - DO NOT create new files except in cases of extreme necessity
            - Explore all directories to find all relevant files
            - Examine the complete content of each file
            
            Your tasks:
            1. ANALYZE existing frontend files (HTML, CSS, JS, etc.)
            2. CHECK their quality, functionality and consistency
            3. IDENTIFY problems, bugs or inconsistencies
            4. FIX these problems by directly modifying existing files
            5. IMPROVE UI/UX if necessary
            6. If images, maps, or videos are required, search for appropriate links on the internet:
               - For images, integrate the image URLs directly into the HTML.
               - For maps, create an iframe with the appropriate map URL.
               - For videos, integrate the video URLs and add the necessary HTML tags.
            
            Do NOT recreate the frontend from scratch.
            Focus on correcting and improving the existing code.
            """
            ],
        )

        # Création de l'agent spécialisé dans le développement backend
        backend_developer = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Backend_Developer",
            tools=[file_tools],
            instructions=[
                """
                You are an agent equipped with tools to read, write and browse files.
                You specialize in VERIFYING and IMPROVING backend code of an existing project.
                
                IMPORTANT INSTRUCTIONS:
                - ANALYZE EXHAUSTIVELY ALL backend files in the project
                - DO NOT create new files except in cases of extreme necessity
                - Systematically explore all directories to identify all files
                - Thoroughly examine the complete content of each file
                
                Your tasks:
                1. ANALYZE existing backend files
                2. VERIFY business logic, database connections, APIs, etc.
                3. IDENTIFY bugs, performance issues, security vulnerabilities
                4. FIX these problems by directly modifying existing files
                5. ENSURE consistency with the frontend
                
                Do NOT recreate the backend from scratch.
                Focus on correcting and improving the existing code.
                """
            ],
        )

        # Création du chef de projet qui coordonne les autres agents
        project_manager = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Project_Manager",
            team=[
                frontend_developer,
                backend_developer
            ],
            tools=[file_tools],
            instructions=[
                """
                You are an expert agent in project management and code verification.
                Your mission is to VERIFY and IMPROVE a project that was just generated by AI.
                
                CRUCIAL INSTRUCTIONS:
                - EXHAUSTIVELY analyze ALL project files without exception
                - DO NOT create new files except in cases of extreme necessity
                - Ensure your team meticulously explores all directories
                - Verify that each file is examined in depth
                - Prioritize modifying existing files rather than creating new ones
                
                Your responsibility is to ensure that:
                - You are working on an EXISTING project that has already been generated
                - Do NOT try to create a new project from scratch
                - Focus on VERIFYING and IMPROVING the existing code
                
                Here is your work process:
                1. ANALYZE the current state of the project in the specified directory
                2. ASK Frontend_Developer to verify and improve the frontend code
                3. ASK Backend_Developer to verify and improve the backend code
                4. CHECK the overall coherence of the project and make sure it works correctly
                5. FINALIZE by writing a completion message in a file named 'verification_complete.txt' at the root directory
                
                For each agent you direct, give PRECISE instructions on what they should verify
                and improve in the existing project.
                
                When you've completed your work, make sure to create a verification_complete.txt file with a
                summary of all improvements made to indicate the verification process is finished.
                """
            ],
            markdown=True,
            show_tool_calls=True,
            add_history_to_messages=True,
        )

        # Lancement de l'équipe d'agents
        logger.info("Starting the verification process with the agent team...")
        
        # Préparation de la description du projet basée sur le contexte
        project_description = f"""
        Verify and optimize the project that has just been generated in the directory {abs_path}.
        
        IMPORTANT GUIDELINES:
        - EXPLORE ALL CONTENT of the folder and its subfolders without exception
        - EXAMINE in detail EACH project file
        - DO NOT create new files except in cases of extreme necessity
        - Prioritize modification and improvement of existing files
        
        The project is: {project_context.get('requirements', {}).get('app_name', 'Generated Application')}
        
        Description: {project_context.get('requirements', {}).get('app_description', 'Web Application')}
        
        Technical stack: {project_context.get('architecture', {}).get('language', 'Python/JavaScript')}
        
        DO NOT CREATE a new project. Your mission is to VERIFY, FIX, and IMPROVE the existing project.
        
        Start by SYSTEMATICALLY exploring the directory and analyzing ALL existing files before suggesting modifications.
        
        After completion, create a verification_complete.txt file at the project root with a summary of improvements made.
        """
        
        # Lancer les agents sans attendre leur achèvement (mode asynchrone)
        logger.info("Launching agent team in background...")
        project_manager.run(project_description, wait_for_completion=False)
        
        # Wait for a short time to ensure the agent is properly initialized
        time.sleep(2)
        
        logger.info("Agent team launched in background. Continuing main flow.")
        
        # Marquer l'équipe comme lancée pour éviter les lancements multiples
        _verification_team_launched = True
        
        # Give some feedback about agent team verification continuing in background
        logger.info(f"Agent team is running in the background and will continue to optimize the project at {abs_path}")
        logger.info("You can check for a verification_complete.txt file in the project directory when they finish")
        
        # Create a placeholder to indicate verification is in progress
        try:
            with open(os.path.join(abs_path, 'verification_in_progress.txt'), 'w') as f:
                f.write(f"Verification started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("The agent team is working in the background to optimize your project.\n")
                f.write("This file will be replaced by 'verification_complete.txt' when finished.\n")
        except Exception as e:
            logger.warning(f"Could not create verification status file: {str(e)}")
        
        # Create a flag file to signal that no further validation is needed
        try:
            with open(os.path.join(abs_path, 'skip_additional_validation.flag'), 'w') as f:
                f.write("This file indicates that no further validation should be performed.\n")
        except Exception as e:
            logger.warning(f"Could not create validation flag file: {str(e)}")
            
        # Return True to indicate no further validation is needed
        return True
        
    except ImportError as e:
        logger.error(f"Unable to import agno library: {str(e)}")
        logger.info("Make sure the 'agno' library is installed to use the agent team")
        return False
    except Exception as e:
        logger.error(f"Error during agent team execution: {str(e)}")
        return False
