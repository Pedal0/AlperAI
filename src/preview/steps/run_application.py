"""
Exécute l'application générée.
"""
import os
import time
import subprocess


def run_application(project_dir, run_command, venv_path=None):
    try:
        # Modifier la commande pour utiliser l'environnement virtuel si disponible
        if venv_path:
            if os.name == 'nt':  # Windows
                python_path = venv_path / "Scripts" / "python"
                run_command = run_command.replace("python ", f'"{python_path}" ')
                if "flask" in run_command.lower():
                    flask_path = venv_path / "Scripts" / "flask"
                    run_command = run_command.replace("flask ", f'"{flask_path}" ')
                if "streamlit" in run_command.lower():
                    streamlit_path = venv_path / "Scripts" / "streamlit"
                    run_command = run_command.replace("streamlit ", f'"{streamlit_path}" ')
            else:  # Unix/Linux/Mac
                python_path = venv_path / "bin" / "python"
                run_command = run_command.replace("python ", f'"{python_path}" ')
                if "flask" in run_command.lower():
                    flask_path = venv_path / "bin" / "flask"
                    run_command = run_command.replace("flask ", f'"{flask_path}" ')
                if "streamlit" in run_command.lower():
                    streamlit_path = venv_path / "bin" / "streamlit"
                    run_command = run_command.replace("streamlit ", f'"{streamlit_path}" ')
        if "flask run" in run_command and "--host" not in run_command:
            run_command += " --host=0.0.0.0"
        if "streamlit run" in run_command and "--server.port" not in run_command:
            run_command += " --server.port=8501"
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if "flask" in run_command.lower():
            env["FLASK_ENV"] = "development"
            env["FLASK_DEBUG"] = "1"
        st.info(f"Démarrage de l'application: {run_command}")
        process = subprocess.Popen(
            run_command,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1
        )
        time.sleep(2)
        if process.poll() is not None:
            st.error(f"Le processus s'est terminé prématurément avec le code {process.returncode}")
            stderr_output = process.stderr.read() if process.stderr else "Pas d'erreur disponible"
            st.error(f"Erreur: {stderr_output}")
            return None, run_command
        return process, run_command
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de l'application: {e}")
        return None, run_command
