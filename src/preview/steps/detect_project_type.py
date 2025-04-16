"""
Détecte le type de projet à partir du dossier projet.
"""
import json
from pathlib import Path

class ProjectType:
    FLASK = "flask"
    EXPRESS = "express"
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    STATIC = "static"
    UNKNOWN = "unknown"

def detect_project_type(project_dir: str) -> str:
    project_dir = Path(project_dir)
    # Détection Flask
    for file in ["app.py", "main.py", "server.py", "run.py"]:
        if (project_dir / file).exists():
            with open(project_dir / file, "r", encoding="utf-8") as f:
                content = f.read()
                if "import flask" in content or "from flask import" in content:
                    return ProjectType.FLASK
    # Détection Node.js/React/Vue/Angular
    if (project_dir / "package.json").exists():
        try:
            with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                package_json = json.load(f)
                dependencies = package_json.get("dependencies", {})
                devDependencies = package_json.get("devDependencies", {})
                all_dependencies = {**dependencies, **devDependencies}
                if "express" in all_dependencies:
                    return ProjectType.EXPRESS
                elif "react" in all_dependencies or "react-dom" in all_dependencies:
                    return ProjectType.REACT
                elif "vue" in all_dependencies:
                    return ProjectType.VUE
                elif "angular" in all_dependencies or "@angular/core" in all_dependencies:
                    return ProjectType.ANGULAR
                elif "tailwindcss" in all_dependencies:
                    return ProjectType.REACT
                if dependencies or devDependencies:
                    return ProjectType.REACT
        except:
            return ProjectType.REACT
    # Détection site statique
    if (project_dir / "index.html").exists() or (project_dir / "public" / "index.html").exists():
        if list(project_dir.glob("**/*.js")) or list(project_dir.glob("**/*.ts")):
            if (project_dir / "package.json").exists():
                return ProjectType.REACT
        return ProjectType.STATIC
    return ProjectType.UNKNOWN
