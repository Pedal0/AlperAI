"""
Installe les dépendances du projet.
"""
import os
import subprocess
import streamlit as st

def install_dependencies(project_dir, commands, venv_path=None):
    try:
        output = []
        for cmd in commands:
            # Modifier la commande pour utiliser l'environnement virtuel si disponible
            if venv_path:
                if os.name == 'nt':  # Windows
                    pip_path = venv_path / "Scripts" / "pip"
                    cmd = cmd.replace("pip install", f'"{pip_path}" install')
                else:  # Unix/Linux/Mac
                    pip_path = venv_path / "bin" / "pip"
                    cmd = cmd.replace("pip install", f'"{pip_path}" install')
            st.info(f"Exécution: {cmd}")
            process = subprocess.run(
                cmd, 
                shell=True, 
                cwd=project_dir, 
                capture_output=True, 
                text=True
            )
            if process.returncode != 0:
                st.warning(f"Commande '{cmd}' a échoué avec le code {process.returncode}")
                st.warning(f"Erreur: {process.stderr}")
                continue
            output.append(f"Commande '{cmd}' exécutée avec succès")
            output.append(process.stdout)
        if output:
            return True, "\n".join(output)
        else:
            return False, "Toutes les commandes d'installation ont échoué"
    except subprocess.CalledProcessError as e:
        return False, f"Erreur lors de l'installation des dépendances: {e}\nSortie: {e.stdout}\nErreur: {e.stderr}"
    except Exception as e:
        return False, f"Erreur inattendue: {e}"
