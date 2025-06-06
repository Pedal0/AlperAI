"""
Installation et configuration automatique du serveur codebase-mcp.
"""

import subprocess
import sys
import logging
import os
from pathlib import Path

def check_node_and_npm():
    """Vérifie que Node.js et npm sont installés."""
    try:
        # Sur Windows, utiliser PowerShell pour accéder aux variables d'environnement
        commands = [
            "powershell.exe -Command \"node --version\"",
            "powershell.exe -Command \"npm --version\""
        ]
        
        # Vérifier Node.js
        node_result = subprocess.run(commands[0], capture_output=True, text=True, shell=True)
        npm_result = subprocess.run(commands[1], capture_output=True, text=True, shell=True)
        
        if node_result.returncode == 0 and npm_result.returncode == 0:
            logging.info(f"Node.js version: {node_result.stdout.strip()}")
            logging.info(f"npm version: {npm_result.stdout.strip()}")
            return True
        else:
            logging.error(f"Node.js returncode: {node_result.returncode}, stderr: {node_result.stderr}")
            logging.error(f"npm returncode: {npm_result.returncode}, stderr: {npm_result.stderr}")
            
            # Essayer une approche alternative avec where
            try:
                where_node = subprocess.run("powershell.exe -Command \"Get-Command node\"", capture_output=True, text=True, shell=True)
                where_npm = subprocess.run("powershell.exe -Command \"Get-Command npm\"", capture_output=True, text=True, shell=True)
                
                if where_node.returncode == 0 and where_npm.returncode == 0:
                    logging.info("Node.js and npm found via Get-Command")
                    return True
                    
            except Exception as e2:
                logging.error(f"Alternative check failed: {e2}")
            
            return False
    except Exception as e:
        logging.error(f"Error checking Node.js/npm: {e}")
        return False

def install_codebase_mcp():
    """Installe le serveur codebase-mcp depuis GitHub."""
    try:
        logging.info("Installing codebase-mcp from GitHub...")
        
        # Créer un répertoire temporaire pour le build
        import tempfile
        temp_dir = tempfile.mkdtemp()
        logging.info(f"Using temporary directory: {temp_dir}")
        
        # Clone le repository
        logging.info("Cloning codebase-mcp repository...")
        clone_result = subprocess.run(
            f"powershell.exe -Command \"cd '{temp_dir}'; git clone https://github.com/DeDeveloper23/codebase-mcp.git\"",
            capture_output=True,
            text=True,
            timeout=120,
            shell=True
        )
        
        if clone_result.returncode != 0:
            logging.error(f"Failed to clone repository: {clone_result.stderr}")
            return False
        
        logging.info("Repository cloned successfully!")
          # Navigate to project directory et install dependencies
        project_dir = os.path.join(temp_dir, "codebase-mcp")
        logging.info("Installing dependencies...")
        
        # Corriger le package.json pour utiliser la version disponible de repomix
        logging.info("Fixing package.json to use available repomix version...")
        package_json_path = os.path.join(project_dir, "package.json")
        
        try:
            import json
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # Remplacer repomix ^1.0.0 par la dernière version disponible
            if 'dependencies' in package_data and 'repomix' in package_data['dependencies']:
                package_data['dependencies']['repomix'] = '^0.3.8'
                logging.info("Updated repomix dependency to ^0.3.8")
            
            with open(package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2)
            
        except Exception as e:
            logging.warning(f"Could not fix package.json: {e}")
        
        install_deps_result = subprocess.run(
            f"powershell.exe -Command \"cd '{project_dir}'; npm install\"",
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        
        if install_deps_result.returncode != 0:
            logging.error(f"Failed to install dependencies: {install_deps_result.stderr}")
            return False
        
        logging.info("Dependencies installed!")
        
        # Build the project
        logging.info("Building the project...")
        build_result = subprocess.run(
            f"powershell.exe -Command \"cd '{project_dir}'; npm run build\"",
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        
        if build_result.returncode != 0:
            logging.error(f"Failed to build project: {build_result.stderr}")
            return False
        
        logging.info("Project built successfully!")
        
        # Install globally
        logging.info("Installing globally...")
        global_install_result = subprocess.run(
            f"powershell.exe -Command \"cd '{project_dir}'; npm install -g .\"",
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        
        if global_install_result.returncode != 0:
            logging.error(f"Failed to install globally: {global_install_result.stderr}")
            return False
        
        logging.info("Global installation completed!")
        
        # Install RepoMix dependency
        logging.info("Installing RepoMix dependency...")
        repomix_result = subprocess.run(
            "powershell.exe -Command \"codebase-mcp install\"",
            capture_output=True,
            text=True,
            timeout=300,
            shell=True
        )
        
        if repomix_result.returncode != 0:
            logging.warning(f"RepoMix installation failed: {repomix_result.stderr}")
            logging.info("Trying to install RepoMix directly...")
            # Fallback: installer RepoMix directement
            direct_repomix_result = subprocess.run(
                "powershell.exe -Command \"npm install -g repomix\"",
                capture_output=True,
                text=True,
                timeout=300,
                shell=True
            )
            if direct_repomix_result.returncode != 0:
                logging.error(f"Direct RepoMix installation also failed: {direct_repomix_result.stderr}")
                return False
        
        logging.info("RepoMix installed successfully!")
        
        # Cleanup temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
            
    except subprocess.TimeoutExpired:
        logging.error("Installation timed out")
        return False
    except Exception as e:
        logging.error(f"Error during installation: {e}")
        return False

def verify_installation():
    """Vérifie que l'installation a réussi."""
    try:
        # Vérifier codebase-mcp avec PowerShell
        result = subprocess.run("powershell.exe -Command \"codebase-mcp version\"", capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            logging.info(f"codebase-mcp is working: {result.stdout}")
            return True
        else:
            # Essayer avec npx
            npx_result = subprocess.run("powershell.exe -Command \"npx codebase-mcp version\"", capture_output=True, text=True, shell=True)
            if npx_result.returncode == 0:
                logging.info(f"codebase-mcp is working via npx: {npx_result.stdout}")
                return True
            else:
                logging.error(f"codebase-mcp verification failed: {result.stderr}")
                logging.error(f"npx verification also failed: {npx_result.stderr}")
                return False
            
    except Exception as e:
        logging.error(f"Error verifying installation: {e}")
        return False

def setup_codebase_mcp():
    """Configuration complète du serveur codebase-mcp."""
    logging.info("Starting codebase-mcp setup...")
    
    # Vérifier les prérequis
    if not check_node_and_npm():
        logging.error("Node.js and npm are required but not found!")
        logging.error("Please install Node.js from https://nodejs.org/")
        return False
    
    # Installer codebase-mcp
    if not install_codebase_mcp():
        logging.error("Failed to install codebase-mcp")
        return False
    
    # Vérifier l'installation
    if not verify_installation():
        logging.error("Installation verification failed")
        return False
    
    logging.info("✅ codebase-mcp setup completed successfully!")
    logging.info("The system is now ready to use advanced codebase analysis.")
    return True

def is_codebase_mcp_available():
    """Vérifie si codebase-mcp est disponible."""
    try:
        result = subprocess.run("powershell.exe -Command \"codebase-mcp version\"", capture_output=True, text=True, shell=True)
        return result.returncode == 0
    except:
        return False

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    success = setup_codebase_mcp()
    sys.exit(0 if success else 1)