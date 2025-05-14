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
Fonction utilitaire : ajout ou mise à jour d'un outil utilisé dans le process_state.
"""
def add_used_tool(process_state, name, details=None):
    existing_tool = next((tool for tool in process_state['used_tools_details'] if tool['name'] == name), None)
    if existing_tool:
        if details:
            if isinstance(existing_tool['details'], list) and isinstance(details, list):
                existing_tool['details'] = list(set(existing_tool['details'] + details))
            else:
                existing_tool['details'] = details
    else:
        process_state['used_tools_details'].append({'name': name, 'details': details if details is not None else []})
