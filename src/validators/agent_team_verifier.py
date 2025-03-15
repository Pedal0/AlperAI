import logging
import time
import os
from typing import Dict, Any
from src.config import AGENT_TEAM_ENABLED, AGENT_TEAM_WAIT_TIME
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.file import FileTools
from pathlib import Path

logger = logging.getLogger(__name__)

def run_verification_team(app_path: str, project_context: Dict[str, Any]) -> None:
    """
    Lance l'équipe d'agents pour vérifier et corriger le projet.
    Cette fonction ne retourne rien, les agents travaillent de façon autonome.
    
    Args:
        app_path: Chemin du projet généré
        project_context: Contexte du projet (requirements, architecture, etc.)
    """
    if not AGENT_TEAM_ENABLED:
        logger.info("L'équipe d'agents de vérification est désactivée")
        return
    
    logger.info(f"Lancement de l'équipe d'agents pour vérifier le projet à {app_path}")
    
    try:
        # Import des dépendances nécessaires pour les agents

        
        # Utilisation du chemin fourni par l'utilisateur
        abs_path = os.path.abspath(app_path)
        logger.info(f"Les agents travaillent sur le chemin absolu: {abs_path}")
        
        # Création des outils pour la manipulation des fichiers
        file_tools = FileTools(Path(abs_path), True, True, True)
        
        # Création de l'agent spécialisé dans la structure du projet
        structure_creator = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Structure_Creator",
            tools=[file_tools],
            instructions=[
                """
                Tu es un agent équipé d'un outil pour lire, écrire et parcourir des fichiers.
                Tu es spécialisé dans la VÉRIFICATION et L'AMÉLIORATION de la structure d'un projet existant.
                
                Tes tâches:
                1. ANALYSER la structure actuelle du projet
                2. VÉRIFIER si tous les fichiers essentiels sont présents
                3. IDENTIFIER les problèmes de structure ou d'organisation
                4. CORRIGER la structure si nécessaire en modifiant ou ajoutant des fichiers
                
                N'efface PAS le projet existant pour en créer un nouveau.
                Concentre-toi uniquement sur l'amélioration de la structure actuelle.
                """
            ],
            markdown=True,
            show_tool_calls=True,
            add_history_to_messages=True,
        )

        # Création de l'agent spécialisé dans le développement frontend
        frontend_developer = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Frontend_Developer",
            tools=[file_tools],
            instructions=[
                """
                Tu es un agent équipé d'un outil pour lire, écrire et parcourir des fichiers.
                Tu es spécialisé dans la VÉRIFICATION et L'AMÉLIORATION du code frontend d'un projet existant.
                
                Tes tâches:
                1. ANALYSER les fichiers frontend existants (HTML, CSS, JS, etc.)
                2. VÉRIFIER leur qualité, fonctionnalité et cohérence
                3. IDENTIFIER les problèmes, bugs ou incohérences
                4. CORRIGER ces problèmes en modifiant directement les fichiers
                5. AMÉLIORER l'UI/UX si nécessaire
                
                Ne recrée PAS le frontend à partir de zéro.
                Concentre-toi sur la correction et l'amélioration du code existant.
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
                Tu es un agent équipé d'un outil pour lire, écrire et parcourir des fichiers.
                Tu es spécialisé dans la VÉRIFICATION et L'AMÉLIORATION du code backend d'un projet existant.
                
                Tes tâches:
                1. ANALYSER les fichiers backend existants
                2. VÉRIFIER la logique métier, les connexions à la base de données, les API, etc.
                3. IDENTIFIER les bugs, problèmes de performance, failles de sécurité
                4. CORRIGER ces problèmes en modifiant directement les fichiers
                5. ASSURER la cohérence avec le frontend
                
                Ne recrée PAS le backend à partir de zéro.
                Concentre-toi sur la correction et l'amélioration du code existant.
                """
            ],
        )

        # Création du chef de projet qui coordonne les autres agents
        project_manager = Agent(
            model=OpenAIChat("gpt-4o-mini"),
            name="Project_Manager",
            team=[
                structure_creator,
                frontend_developer,
                backend_developer
            ],
            instructions=[
                """
                Tu es un agent expert en gestion de projet et en vérification de code.
                Ta mission est de VÉRIFIER et AMÉLIORER un projet qui vient d'être généré par IA.
                
                Instructions importantes:
                - Tu travailles sur un projet EXISTANT qui a déjà été généré
                - N'essaie PAS de créer un nouveau projet à partir de zéro
                - Concentre-toi sur la VÉRIFICATION et l'AMÉLIORATION du code existant
                
                Voici ton processus de travail:
                1. ANALYSE l'état actuel du projet dans le répertoire spécifié
                2. DEMANDE à Structure_Creator de vérifier et corriger la structure du projet
                3. DEMANDE à Frontend_Developer de vérifier et améliorer le code frontend
                4. DEMANDE à Backend_Developer de vérifier et améliorer le code backend
                5. VÉRIFIE la cohérence globale du projet et assure-toi qu'il fonctionne correctement
                
                Pour chaque agent que tu diriges, donne des instructions PRÉCISES sur ce qu'il doit vérifier
                et améliorer dans le projet existant.
                """
            ],
            markdown=True,
            show_tool_calls=True,
            add_history_to_messages=True,
        )

        # Lancement de l'équipe d'agents
        logger.info("Démarrage du processus de vérification avec l'équipe d'agents...")
        
        # Préparation de la description du projet basée sur le contexte
        project_description = f"""
        Vérifie et optimise le projet qui vient d'être généré dans le répertoire {abs_path}.
        
        Le projet est: {project_context.get('requirements', {}).get('app_name', 'Application générée')}
        
        Description: {project_context.get('requirements', {}).get('app_description', 'Application Web')}
        
        Stack technique: {project_context.get('architecture', {}).get('language', 'Python/JavaScript')}
        
        NE CRÉE PAS un nouveau projet. Ta mission est de VÉRIFIER, CORRIGER et AMÉLIORER le projet existant.
        
        Commence par explorer le répertoire et analyser les fichiers existants avant de suggérer des modifications.
        """
        
        # Lancer les agents et attendre qu'ils terminent
        project_manager.run(project_description)
        
        logger.info(f"Attente de {AGENT_TEAM_WAIT_TIME} secondes pour que les agents terminent...")
        time.sleep(AGENT_TEAM_WAIT_TIME)
        
        logger.info("Vérification par l'équipe d'agents terminée avec succès")
        
    except ImportError as e:
        logger.error(f"Impossible d'importer la bibliothèque agno: {str(e)}")
        logger.info("Assurez-vous que la bibliothèque 'agno' est installée pour utiliser l'équipe d'agents")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de l'équipe d'agents: {str(e)}")
