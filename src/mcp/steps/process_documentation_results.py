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
Traite les résultats de la recherche de documentation MCP.
"""
def process_documentation_results(doc_results):
    """
    Process documentation search results into code-relevant information.
    
    Args:
        doc_results (str): Raw documentation search results
        
    Returns:
        str: Processed documentation information useful for coding
    """
    # Extract code examples if present
    code_pattern = r'```(?:\w+)?\n(.*?)\n```'
    code_blocks = re.findall(code_pattern, doc_results, re.DOTALL)
    
    processed_info = ["### Documentation Information ###"]
    processed_info.append(doc_results)
    
    if code_blocks:
        processed_info.append("\n### Extracted Code Examples ###")
        for i, code in enumerate(code_blocks, 1):
            processed_info.append(f"Example {i}:\n{code}")
    
    return "\n".join(processed_info)
    pass



