import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ContextEnricher:
    """
    Enrichit le contexte fourni aux modèles d'IA lors de la génération de code
    en fournissant des informations sur la structure du projet et les fichiers existants.
    """
    
    @staticmethod
    def enrich_generation_context(project_context: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        Enrichit le contexte du projet avec des informations sur la structure des fichiers
        et le contenu des fichiers existants.
        
        Args:
            project_context: Le contexte du projet actuel
            output_dir: Le répertoire de sortie du projet
            
        Returns:
            Dict avec le contexte enrichi
        """
        enriched_context = project_context.copy()
        
        # Ajouter la structure du projet
        file_structure = ContextEnricher._get_project_structure(output_dir)
        enriched_context['file_structure'] = file_structure
        
        # Ajouter le contenu des fichiers existants
        existing_files_content = ContextEnricher._get_existing_files_content(output_dir, file_structure)
        enriched_context['existing_files'] = existing_files_content
        
        logger.info(f"Context enriched with {len(file_structure)} files structure and {len(existing_files_content)} file contents")
        
        return enriched_context
    
    @staticmethod
    def _get_project_structure(root_dir: str) -> List[str]:
        """
        Récupère la structure complète du projet sous forme de liste de chemins de fichiers.
        
        Args:
            root_dir: Le répertoire racine du projet
            
        Returns:
            Liste des chemins de fichiers relatifs
        """
        file_paths = []
        
        for dirpath, _, filenames in os.walk(root_dir):
            rel_dirpath = os.path.relpath(dirpath, root_dir)
            
            for filename in filenames:
                if rel_dirpath == '.':
                    file_paths.append(filename)
                else:
                    file_paths.append(os.path.join(rel_dirpath, filename))
        
        return sorted(file_paths)
    
    @staticmethod
    def _get_existing_files_content(root_dir: str, file_paths: List[str], max_files: int = 20, max_size: int = 50000) -> Dict[str, str]:
        """
        Récupère le contenu des fichiers existants, en se limitant aux fichiers les plus pertinents.
        
        Args:
            root_dir: Le répertoire racine du projet
            file_paths: Liste des chemins de fichiers à considérer
            max_files: Nombre maximum de fichiers à inclure
            max_size: Taille maximale totale du contenu (en caractères)
            
        Returns:
            Dictionnaire {chemin_fichier: contenu}
        """
        existing_files = {}
        total_size = 0
        
        # Prioriser les fichiers importants pour le contexte
        priority_extensions = ['.html', '.css', '.js', '.py', '.json']
        priority_files = []
        other_files = []
        
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in priority_extensions:
                priority_files.append(file_path)
            else:
                other_files.append(file_path)
        
        # Trier par priorité
        sorted_files = priority_files + other_files
        
        for file_path in sorted_files[:max_files]:
            full_path = os.path.join(root_dir, file_path)
            
            try:
                if os.path.getsize(full_path) > 100000:  # Ignorer les fichiers trop volumineux
                    continue
                    
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                if len(content) + total_size > max_size:
                    # Limiter la taille pour éviter d'atteindre les limites du contexte de l'IA
                    content = content[:max_size - total_size] + "\n... (content truncated)"
                
                existing_files[file_path] = content
                total_size += len(content)
                
                if total_size >= max_size:
                    break
                    
            except Exception as e:
                logger.warning(f"Couldn't read file {file_path}: {str(e)}")
        
        return existing_files
