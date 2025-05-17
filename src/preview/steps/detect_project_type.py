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
    PHP = "php"
    STREAMLIT = "streamlit"
    UNKNOWN = "unknown"
