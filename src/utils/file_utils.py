import os
import sys


def suggest_directories():
    """Renvoie une liste de répertoires suggérés selon la plateforme"""
    home = os.path.expanduser('~')
    suggestions = [
        os.path.join(home, "Documents"),
        os.path.join(home, "Desktop"),
        home
    ]

    # Répertoires spécifiques à la plateforme
    if sys.platform == "darwin":  # macOS
        suggestions.append(os.path.join(home, "Documents", "Projects"))
    elif sys.platform == "win32":  # Windows
        suggestions.append(os.path.join(home, "Projects"))

    return [path for path in suggestions if os.path.exists(path)]


def create_zip(directory):
    """Crée une archive zip d'un répertoire"""
    import zipfile
    import io

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(
                    file_path,
                    os.path.relpath(file_path, os.path.join(directory, '..'))
                )

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
