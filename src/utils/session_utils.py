# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

"""
Utilities for managing Flask session data to prevent cookie size issues.
"""

def clean_generation_result_for_session(result):
    """
    Nettoie les données de résultat de génération pour éviter que la session cookie devienne trop grande.
    
    Args:
        result (dict): Le résultat de génération original
        
    Returns:
        dict: Le résultat nettoyé avec des données tronquées
    """
    if not result:
        return result
    
    cleaned_result = result.copy()
    
    # Limiter la liste des fichiers aux 50 premiers pour éviter une session trop large
    if 'file_list' in cleaned_result:
        file_list = cleaned_result['file_list']
        if isinstance(file_list, list) and len(file_list) > 50:
            cleaned_result['file_list'] = file_list[:50] + [f'... ({len(file_list) - 50} more files)']
    
    # Limiter la liste des fichiers encore vides aussi
    if 'files_still_empty' in cleaned_result:
        empty_files = cleaned_result['files_still_empty']
        if isinstance(empty_files, list) and len(empty_files) > 20:
            cleaned_result['files_still_empty'] = empty_files[:20] + [f'... ({len(empty_files) - 20} more files)']
    
    # Limiter les détails des outils utilisés
    if 'used_tools' in cleaned_result:
        cleaned_tools = []
        for tool in cleaned_result['used_tools']:
            if isinstance(tool, dict):
                tool_copy = tool.copy()
                # Limiter les détails si c'est une liste trop longue
                if isinstance(tool_copy.get('details'), list) and len(tool_copy['details']) > 10:
                    original_count = len(tool_copy['details'])
                    tool_copy['details'] = tool_copy['details'][:10] + [f'... ({original_count - 10} more items)']
                # Limiter la taille des détails si c'est une string trop longue
                elif isinstance(tool_copy.get('details'), str) and len(tool_copy['details']) > 1000:
                    tool_copy['details'] = tool_copy['details'][:1000] + '... (truncated)'
                cleaned_tools.append(tool_copy)
            else:
                cleaned_tools.append(tool)
        cleaned_result['used_tools'] = cleaned_tools
    
    # Raccourcir le prompt reformulé s'il est trop long
    if 'reformulated_prompt' in cleaned_result:
        prompt = cleaned_result['reformulated_prompt']
        if isinstance(prompt, str) and len(prompt) > 2000:
            cleaned_result['reformulated_prompt'] = prompt[:2000] + '... (truncated for session storage)'
    
    # Raccourcir le prompt original aussi s'il est trop long
    if 'prompt' in cleaned_result:
        prompt = cleaned_result['prompt']
        if isinstance(prompt, str) and len(prompt) > 1500:
            cleaned_result['prompt'] = prompt[:1500] + '... (truncated for session storage)'
    
    return cleaned_result


def clean_session_after_generation(session):
    """
    Nettoie la session après une génération réussie pour réduire la taille de la cookie.
    NOUVELLE VERSION: Plus agressive pour éviter les cookies trop larges.
    
    Args:
        session: L'objet session Flask
    """
    # Supprimer l'API key après génération pour sécurité et réduction de taille
    session.pop('api_key', None)
    
    # Supprimer d'autres données temporaires qui ne sont plus nécessaires
    session.pop('generation_task_id', None)
    
    # Supprimer aussi d'autres données volumineuses temporaires
    session.pop('use_mcp', None)
    session.pop('frontend_framework', None)
    session.pop('include_animations', None)
    session.pop('prompt', None)  # Maintenant stocké côté serveur
    
    # Garder seulement les données essentielles minimales:
    # - generation_result (version minimale avec generation_id)
    # - target_dir (pour compatibilité)
    # - model (pour les futures itérations)


def estimate_session_size(session):
    """
    Estime la taille de la session en bytes pour debugging.
    
    Args:
        session: L'objet session Flask
        
    Returns:
        int: Taille estimée en bytes
    """
    import json
    try:
        # Convertit la session en JSON puis calcule la taille
        session_str = json.dumps(dict(session), default=str)
        return len(session_str.encode('utf-8'))
    except Exception:
        return -1  # Impossible de calculer la taille
