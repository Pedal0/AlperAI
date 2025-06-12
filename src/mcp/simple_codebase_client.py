"""
Client MCP simplifié pour l'analyse de codebase utilisant RepoMix directement.
Alternative au serveur codebase-mcp officiel.
"""

import subprocess
import logging
import tempfile
import os
import json
from pathlib import Path

class SimpleCodebaseClient:
    """Client simplifié pour analyser les codebases avec RepoMix."""
    
    def __init__(self):
        # Use the robust check before any install attempt
        if self.check_repomix_thoroughly():
            self.repomix_available = True
        else:
            # Only attempt automatic install if not present, but do not block or prompt interactively
            logging.warning("RepoMix not detected. Please install it globally with 'npm install -g repomix' as described in the README.")
            self.repomix_available = self._check_repomix()
            if not self.repomix_available:
                logging.error("RepoMix is not available. Codebase analysis will be skipped. See README for installation instructions.")
    
    def _check_repomix(self):
        """Vérifie si RepoMix est disponible."""
        try:
            result = subprocess.run(
                "powershell.exe -Command \"npx repomix --version\"",
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )
            if result.returncode == 0:
                logging.info(f"RepoMix available: {result.stdout.strip()}")
                return True
            else:
                logging.warning("RepoMix not available, will try to install")
                return self._install_repomix()
        except Exception as e:
            logging.error(f"Error checking RepoMix: {e}")
            return False
    
    def _install_repomix(self):
        """Installe RepoMix si nécessaire."""
        try:
            logging.info("Installing RepoMix...")
            result = subprocess.run(
                "powershell.exe -Command \"npm install -g repomix\"",
                capture_output=True,
                text=True,
                shell=True,
                timeout=300
            )
            if result.returncode == 0:
                logging.info("RepoMix installed successfully")
                return True
            else:
                logging.error(f"Failed to install RepoMix: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error installing RepoMix: {e}")
            return False
    
    def get_codebase_analysis(self, directory_path, output_format="markdown", include_summary=True):
        """
        Analyse une codebase et retourne le résultat formaté.
        
        Args:
            directory_path: Chemin vers le répertoire à analyser
            output_format: Format de sortie ("markdown", "xml", "plain")
            include_summary: Inclure un résumé de la structure
        
        Returns:
            tuple: (success, content/error_message)
        """
        if not self.repomix_available:
            return False, "RepoMix not available"
        
        try:
            # Créer un fichier temporaire pour la sortie
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as temp_file:
                temp_output = temp_file.name
            
            # Construire la commande RepoMix
            cmd_parts = [
                "powershell.exe", "-Command",
                f"cd '{directory_path}'; npx repomix"
            ]            # Options RepoMix (basées sur la version 0.3.8)
            options = []
            if output_format == "xml":
                options.append("--style xml")
            elif output_format == "plain":
                options.append("--style plain")
            else:
                options.append("--style markdown")
            
            # Ajouter les options utiles pour l'analyse
            options.append("--output-show-line-numbers")  # Numéros de ligne
            options.append("--verbose")  # Logging détaillé
            if not include_summary:
                options.append("--no-file-summary")  # Désactiver le résumé si demandé
            
            # Ajouter les options à la commande
            if options:
                cmd_parts[2] += " " + " ".join(options)
            
            # Ajouter la sortie vers le fichier temporaire
            cmd_parts[2] += f" --output '{temp_output}'"
            
            logging.info(f"Running RepoMix analysis on: {directory_path}")
            
            # Exécuter RepoMix
            result = subprocess.run(
                " ".join(cmd_parts),
                capture_output=True,
                text=True,
                shell=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                # Lire le résultat
                try:
                    with open(temp_output, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Nettoyer le fichier temporaire
                    os.unlink(temp_output)
                    
                    if content.strip():
                        logging.info("Codebase analysis completed successfully")
                        return True, content
                    else:
                        return False, "RepoMix produced empty output"
                        
                except Exception as e:
                    logging.error(f"Error reading RepoMix output: {e}")
                    return False, f"Error reading output: {e}"
            else:
                # Nettoyer le fichier temporaire même en cas d'erreur
                try:
                    os.unlink(temp_output)
                except:
                    pass
                
                logging.error(f"RepoMix failed: {result.stderr}")
                return False, f"RepoMix error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            logging.error("RepoMix analysis timed out")
            return False, "Analysis timed out"
        except Exception as e:
            logging.error(f"Error during codebase analysis: {e}")
            return False, str(e)
    
    def analyze_project_structure(self, directory_path):
        """
        Analyse la structure d'un projet et retourne des informations détaillées.
        
        Returns:
            dict: Structure du projet avec métadonnées
        """
        try:
            project_info = {
                "path": directory_path,
                "files": [],
                "directories": [],
                "file_types": {},
                "total_files": 0,
                "total_size": 0
            }
            
            directory_path = Path(directory_path)
            if not directory_path.exists():
                return project_info
            
            # Analyser les fichiers et dossiers
            for item in directory_path.rglob('*'):
                if item.is_file():
                    # Ignorer les fichiers cachés et les répertoires système
                    if any(part.startswith('.') for part in item.parts):
                        continue
                    if any(part in ['node_modules', '__pycache__', '.git', 'venv', 'env'] for part in item.parts):
                        continue
                    
                    try:
                        file_size = item.stat().st_size
                        relative_path = item.relative_to(directory_path)
                        
                        project_info["files"].append({
                            "path": str(relative_path),
                            "size": file_size,
                            "extension": item.suffix.lower()
                        })
                        
                        # Compter par type de fichier
                        ext = item.suffix.lower() or "no_extension"
                        project_info["file_types"][ext] = project_info["file_types"].get(ext, 0) + 1
                        
                        project_info["total_files"] += 1
                        project_info["total_size"] += file_size
                        
                    except (OSError, PermissionError):
                        continue
                        
                elif item.is_dir():
                    if not any(part.startswith('.') for part in item.parts):
                        relative_path = item.relative_to(directory_path)
                        project_info["directories"].append(str(relative_path))
            
            return project_info
            
        except Exception as e:
            logging.error(f"Error analyzing project structure: {e}")
            return {"error": str(e)}

    @staticmethod
    def check_repomix_thoroughly():
        """
        Robustly checks if RepoMix is available in the PATH.
        Returns True if the command works, False otherwise.
        """
        import shutil
        import subprocess
        repomix_path = shutil.which("repomix")
        if not repomix_path:
            logging.warning("RepoMix is not in the PATH.")
            return False
        try:
            result = subprocess.run(
                [repomix_path, "--help"],
                capture_output=True,
                text=True,
                shell=False,
                timeout=20
            )
            if result.returncode == 0 and ("Usage" in result.stdout or "repomix" in result.stdout.lower()):
                logging.info("RepoMix detected and functional.")
                return True
            else:
                logging.warning(f"RepoMix found but did not respond as expected: {result.stdout} {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error during explicit RepoMix check: {e}")
            return False

    @staticmethod
    def prompt_user_to_install_repomix():
        """
        Prompt the user to manually install RepoMix if not available.
        """
        print("\n[RepoMix not detected]")
        print("Please install RepoMix globally by running:")
        print("    npm install -g repomix\n")
        input("Once installed, press Enter to continue...")

def create_simple_codebase_client():
    """Factory function pour créer un client codebase simplifié."""
    return SimpleCodebaseClient()

# Test de fonctionnalité
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    client = SimpleCodebaseClient()
    if client.repomix_available:
        print("✅ Simple codebase client is ready")
        
        # Test sur le répertoire courant
        success, result = client.get_codebase_analysis(".", output_format="markdown")
        if success:
            print(f"✅ Analysis successful, content length: {len(result)}")
        else:
            print(f"❌ Analysis failed: {result}")
    else:
        print("❌ RepoMix not available")