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
Stockage côté serveur pour éviter les problèmes de taille de cookie de session.
"""
import time
from typing import Dict, Any, Optional

# Stockage global côté serveur (en production, utilisez Redis ou une base de données)
_server_storage: Dict[str, Dict[str, Any]] = {}

def store_generation_data(session_id: str, data: Dict[str, Any], ttl_hours: int = 24) -> None:
    """
    Stocke les données de génération côté serveur avec un TTL.
    
    Args:
        session_id: ID unique de la session
        data: Données à stocker
        ttl_hours: Durée de vie en heures
    """
    expiry_time = time.time() + (ttl_hours * 3600)
    _server_storage[session_id] = {
        'data': data,
        'expiry': expiry_time
    }
    
    # Nettoie les données expirées
    _cleanup_expired_data()

def get_generation_data(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les données de génération depuis le stockage serveur.
    
    Args:
        session_id: ID unique de la session
        
    Returns:
        Les données stockées ou None si non trouvées/expirées
    """
    _cleanup_expired_data()
    
    if session_id in _server_storage:
        stored_item = _server_storage[session_id]
        if time.time() < stored_item['expiry']:
            return stored_item['data']
        else:
            # Données expirées, les supprimer
            del _server_storage[session_id]
    
    return None

def delete_generation_data(session_id: str) -> bool:
    """
    Supprime les données de génération du stockage serveur.
    
    Args:
        session_id: ID unique de la session
        
    Returns:
        True si les données ont été supprimées, False si non trouvées
    """
    if session_id in _server_storage:
        del _server_storage[session_id]
        return True
    return False

def _cleanup_expired_data() -> None:
    """Nettoie les données expirées du stockage."""
    current_time = time.time()
    expired_keys = [
        session_id for session_id, item in _server_storage.items()
        if current_time >= item['expiry']
    ]
    
    for key in expired_keys:
        del _server_storage[key]

def get_storage_stats() -> Dict[str, Any]:
    """
    Retourne des statistiques sur le stockage serveur.
    
    Returns:
        Dictionnaire avec les statistiques
    """
    _cleanup_expired_data()
    
    total_sessions = len(_server_storage)
    total_size_estimate = 0
    
    for item in _server_storage.values():
        # Estimation grossière de la taille
        import json
        try:
            data_str = json.dumps(item['data'], default=str)
            total_size_estimate += len(data_str.encode('utf-8'))
        except:
            total_size_estimate += 1000  # Estimation par défaut
    
    return {
        'total_sessions': total_sessions,
        'estimated_total_size_bytes': total_size_estimate,
        'estimated_avg_size_per_session': total_size_estimate // max(total_sessions, 1)
    }
