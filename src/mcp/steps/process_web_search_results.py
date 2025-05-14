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

import re
"""
Traite les résultats de la recherche web MCP.
"""
def process_web_search_results(search_results):
    """
    Process web search results into a useful format for code generation.
    
    Args:
        search_results (str): Raw search results from web search tool
        
    Returns:
        str: Processed and formatted search information
    """
    # Extract key information from the search results
    lines = search_results.strip().split('\n')
    processed_info = []
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Try to extract URLs if present
        urls = re.findall(r'https?://[^\s]+', line)
        if urls:
            for url in urls:
                processed_info.append(f"Source: {url}")
        
        # Add the line itself
        processed_info.append(line)
    
    return "\n".join(processed_info)


    pass