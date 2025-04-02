"""
Utility functions for file operations, structure parsing, and code writing.
"""
import re
import streamlit as st
from pathlib import Path

def parse_structure_and_prompt(response_text):
    """
    Extract the reformulated prompt and cleaned structure from the first API call response.
    
    Args:
        response_text (str): Raw response text from the API
        
    Returns:
        tuple: (reformulated_prompt, structure_lines)
    """
    reformulated_prompt = None
    structure_lines = []
    cleaned_structure_lines = []

    try:
        # Recherche des marqueurs principaux
        prompt_match = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*?)\s*###\s*STRUCTURE\s*###", response_text, re.DOTALL | re.IGNORECASE)
        structure_match = re.search(r"###\s*STRUCTURE\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)

        if prompt_match:
            reformulated_prompt = prompt_match.group(1).strip()
        else:
            # Tentative de trouver le prompt même sans le marqueur structure après
            prompt_match_alt = re.search(r"###\s*REFORMULATED PROMPT\s*###\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
            if prompt_match_alt:
                 reformulated_prompt = prompt_match_alt.group(1).strip()

        if structure_match:
            structure_block = structure_match.group(1).strip()
            # Nettoyage du bloc structure : enlever les ``` et les commentaires #
            structure_block_cleaned = structure_block.strip().strip('`') # Enlève les ``` au début/fin
            potential_lines = structure_block_cleaned.split('\n')

            for line in potential_lines:
                line = line.strip()
                # Ignorer lignes vides ou marqueurs de code seuls
                if not line or line == '```':
                    continue
                # Supprimer les commentaires inline (tout ce qui suit #)
                # Garder la partie avant le #, puis re-strip au cas où il y a des espaces avant #
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                # Ajouter seulement si la ligne n'est pas vide après nettoyage
                if line:
                    cleaned_structure_lines.append(line)
            structure_lines = cleaned_structure_lines # Utiliser la liste nettoyée
        else:
            # Si structure_match échoue, on ne peut pas extraire la structure
             st.warning("Marqueur '### STRUCTURE ###' non trouvé.")

        # --- Gestion des cas où les marqueurs ne sont pas trouvés ou vides ---
        if not reformulated_prompt and not structure_lines:
             st.error("Impossible d'extraire le prompt reformulé ET la structure. Vérifiez le format de réponse de l'IA.")
             st.code(response_text)
             return None, []
        elif not reformulated_prompt:
             st.warning("Prompt reformulé non trouvé, mais structure trouvée. Tentative de continuer.")
             # On pourrait essayer d'utiliser le prompt original comme fallback, mais c'est risqué
             # Pour l'instant, on retourne None pour le prompt, ce qui causera une erreur plus tard (ce qui est ok)
             return None, structure_lines
        elif not structure_lines:
             st.warning("Structure non trouvée, mais prompt reformulé trouvé. Impossible de créer les fichiers.")
             return reformulated_prompt, []

    except Exception as e:
        st.error(f"Erreur lors de l'analyse de la réponse de l'IA (structure/prompt) : {e}")
        st.code(response_text) # Afficher la réponse brute
        return None, []

    # Afficher la structure nettoyée pour le debug
    st.write("Structure détectée et nettoyée :")
    st.code("\n".join(structure_lines), language='text')

    return reformulated_prompt, structure_lines


def create_project_structure(base_path, structure_lines):
    """
    Create folders and empty files based on the cleaned structure.
    
    Args:
        base_path (str): Base directory path
        structure_lines (list): List of file/directory paths
        
    Returns:
        list: List of created paths or None on error
    """
    created_paths = []
    base_path = Path(base_path).resolve() # Obtenir le chemin absolu et normalisé
    st.info(f"Tentative de création de la structure dans : {base_path}")

    if not base_path.is_dir():
        st.error(f"Le chemin de base '{base_path}' n'est pas un dossier valide ou n'existe pas.")
        return None

    if not structure_lines:
        st.warning("Aucune ligne de structure fournie à créer.")
        return [] # Retourner une liste vide, ce n'est pas une erreur fatale

    try:
        for line in structure_lines:
            line = line.strip() # Re-nettoyer au cas où
            if not line: continue # Ignorer lignes vides

            # Sécurité: Vérifier la présence de '..' dans les composants du chemin
            relative_path = Path(line)
            if ".." in relative_path.parts:
                 st.warning(f"⚠️ Chemin contenant '..' ignoré (sécurité) : '{line}'")
                 continue

            item_path = base_path / relative_path

            try:
                # Déterminer si c'est un dossier ou un fichier
                # Path() supprime le '/' final, donc on se fie à la ligne originale
                is_dir = line.endswith('/')

                if is_dir:
                    # Créer le dossier
                    item_path.mkdir(parents=True, exist_ok=True)
                    st.write(f" ✅ Dossier créé/vérifié : {item_path}")
                    created_paths.append(item_path)
                else:
                    # C'est un fichier: Créer les dossiers parents si nécessaire
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    # Créer le fichier vide (ou le vider s'il existe)
                    item_path.touch(exist_ok=True)
                    st.write(f" ✅ Fichier créé/vérifié : {item_path}")
                    created_paths.append(item_path)

            except OSError as e:
                 st.error(f"❌ Erreur OS lors de la création de '{item_path}' depuis la ligne '{line}': {e}")
                 # Continuer avec les autres si possible
            except Exception as e:
                 st.error(f"❌ Erreur inattendue pour '{item_path}' depuis la ligne '{line}': {e}")

        return created_paths
    except Exception as e:
        st.error(f"Erreur majeure lors du traitement de la structure du projet : {e}")
        return None


def parse_and_write_code(base_path, code_response_text):
    """
    Parse code response and write each block to the corresponding file.
    
    Args:
        base_path (str): Base directory path
        code_response_text (str): Raw code generation response
        
    Returns:
        tuple: (files_written, errors, generation_incomplete)
    """
    base_path = Path(base_path).resolve()
    files_written = []
    errors = []
    generation_incomplete = False

    # Vérifier d'abord si la réponse se termine par le marqueur d'incomplétude
    if code_response_text.strip().endswith("GENERATION_INCOMPLETE"):
        generation_incomplete = True
        st.warning("⚠️ L'IA a indiqué que la génération de code est incomplète (limite de tokens probablement atteinte).")
        # Retirer le marqueur pour ne pas interférer avec le parsing du dernier fichier
        code_response_text = code_response_text.strip()[:-len("GENERATION_INCOMPLETE")].strip()

    # Regex pour trouver les blocs de code marqués par --- FILE: path/to/file ---
    # Utiliser re.split pour séparer par le marqueur, en capturant le chemin
    # Le `?` après `.*` le rend non-greedy, important si des marqueurs sont proches
    parts = re.split(r'(---\s*FILE:\s*(.*?)\s*---)', code_response_text, flags=re.IGNORECASE)

    if len(parts) <= 1:
        st.warning("Aucun marqueur '--- FILE: ... ---' trouvé dans la réponse de génération de code.")
        st.info("Tentative d'écriture de toute la réponse dans un fichier 'generated_code.txt'")
        output_file = base_path / "generated_code.txt"
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code_response_text)
            files_written.append(str(output_file))
            st.write(f" ✅ Code brut écrit dans : {output_file}")
        except Exception as e:
             errors.append(f"❌ Impossible d'écrire dans '{output_file}': {e}")
        # On ne peut pas savoir si c'est incomplet dans ce cas sans le marqueur
        return files_written, errors, generation_incomplete

    # Itérer sur les blocs capturés (ignore la première partie avant le premier marqueur)
    # Structure de parts: ['', marker1, path1, code1, marker2, path2, code2, ...]
    for i in range(1, len(parts), 3):
        try:
            # marker = parts[i] # Le marqueur complet (e.g., '--- FILE: src/main.py ---')
            file_path_str = parts[i+1].strip() # Le chemin du fichier extrait
            code_block = parts[i+2].strip()    # Le bloc de code (peut être vide si fin abrupte)

            if not file_path_str:
                st.warning(f"Marqueur trouvé mais chemin de fichier vide ou invalide, bloc ignoré.")
                continue

            # Nettoyage et validation du chemin
            file_path_str = file_path_str.replace('\r', '').strip()
            if not file_path_str: continue # Ignorer si vide après nettoyage

            relative_path = Path(file_path_str)
            if ".." in relative_path.parts: # Sécurité: Vérification de '..'
                 st.warning(f"⚠️ Chemin de fichier '{file_path_str}' contient '..', ignoré pour la sécurité.")
                 continue

            target_file_path = base_path / relative_path

            # S'assurer que le dossier parent existe (créé à l'étape 2, mais sécurité)
            target_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Écrire le code dans le fichier
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(code_block)

            files_written.append(str(target_file_path))
            # st.write(f"   Code écrit dans : {target_file_path}") # Peut être verbeux

        except IndexError:
             # Si la réponse se termine juste après un marqueur sans code
             st.warning(f"Fin de réponse inattendue après le marqueur pour '{parts[i+1].strip() if i+1 < len(parts) else 'dernier fichier'}'. Fichier potentiellement vide ou manquant.")
             continue
        except OSError as e:
            error_msg = f"❌ Erreur d'écriture dans le fichier '{file_path_str}': {e}"
            st.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"❌ Erreur inattendue lors du traitement du fichier '{file_path_str}': {e}"
            st.error(error_msg)
            errors.append(error_msg)

    return files_written, errors, generation_incomplete
