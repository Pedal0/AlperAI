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
Utility functions related to model identification and handling.
"""

def is_free_model(model_name):
    """
    Verify if the model name indicates a free model requiring rate limiting.
    
    Args:
        model_name (str): The model name to check
        
    Returns:
        bool: True if it's a free model, False otherwise
    """
    if not model_name:
        return False
        
    name_lower = model_name.lower()
    return ":free" in name_lower or "google/gemini-flash" in name_lower