"""
Crée et active un environnement virtuel pour le projet.
"""
import sys
import os
import subprocess
from pathlib import Path
import streamlit as st

def setup_virtual_environment(project_dir, venv_command=None):
    try:
        venv_path = Path(project_dir) / "venv"
        # Vérifier si l'environnement virtuel existe déjà
        if venv_path.exists():
            python_exec = venv_path / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")
            if python_exec.exists():
                st.success(f"✅ Environnement virtuel existant détecté à {venv_path}")
                return True, venv_path
            else:
                st.warning(f"⚠️ Dossier venv existant mais incomplet. Suppression et recréation...")
                try:
                    import shutil
                    shutil.rmtree(venv_path)
                except Exception as e:
                    st.error(f"❌ Impossible de supprimer l'environnement virtuel existant: {e}")
                    return False, f"Erreur lors de la suppression de l'environnement virtuel: {e}"
        if not venv_command:
            venv_command = f'"{sys.executable}" -m venv "{venv_path}"'
        else:
            venv_command = venv_command.replace("venv", str(venv_path))
        st.info(f"Création de l'environnement virtuel: {venv_command}")
        result = subprocess.run(
            venv_command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            st.error(f"❌ Échec de la création de l'environnement virtuel: {result.stderr}")
            st.info("🔄 Tentative avec une approche alternative...")
            if os.name == 'nt':
                alt_command = f'pip install virtualenv && virtualenv "{venv_path}"'
                st.info(f"Exécution de: {alt_command}")
                alt_result = subprocess.run(
                    alt_command,
                    shell=True,
                    cwd=project_dir,
                    capture_output=True,
                    text=True
                )
                if alt_result.returncode == 0:
                    st.success("✅ Environnement virtuel créé avec virtualenv")
                    return True, venv_path
                else:
                    return False, f"Échec des deux tentatives de création d'environnement virtuel: {alt_result.stderr}"
            return False, f"Erreur lors de la création de l'environnement virtuel: {result.stderr}"
        python_exec = venv_path / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")
        if not python_exec.exists():
            return False, "L'environnement virtuel a été créé mais le binaire Python est introuvable"
        return True, venv_path
    except subprocess.CalledProcessError as e:
        return False, f"Erreur lors de la création de l'environnement virtuel: {e.stderr}"
    except Exception as e:
        return False, f"Erreur inattendue: {e}"
