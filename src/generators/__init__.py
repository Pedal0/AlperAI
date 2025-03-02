from src.generators.structure_generator import generate_project_structure
from src.generators.file_generator import generate_project_files, generate_file_content
from src.generators.verification_generator import verify_project_files

# Exposer les fonctions pour maintenir la compatibilité avec le code existant
__all__ = ['generate_project_structure', 'generate_project_files', 'generate_file_content', 'verify_project_files']
