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
Traite les résultats des composants frontend MCP.
"""
def process_frontend_component_results(component_results):
    """
    Process frontend component search results to extract usable code.
    
    Args:
        component_results (str): Raw component search results
        
    Returns:
        str: Processed component information with code examples
    """
    # Extract HTML/CSS/JS code
    html_pattern = r'```(?:html)?\n(.*?)\n```'
    css_pattern = r'```(?:css)?\n(.*?)\n```'
    js_pattern = r'```(?:javascript|js)?\n(.*?)\n```'
    
    html_blocks = re.findall(html_pattern, component_results, re.DOTALL)
    css_blocks = re.findall(css_pattern, component_results, re.DOTALL)
    js_blocks = re.findall(js_pattern, component_results, re.DOTALL)
    
    processed_info = ["### Component Information ###"]
    processed_info.append(component_results)
    
    if html_blocks or css_blocks or js_blocks:
        processed_info.append("\n### Extracted Component Code ###")
        
        if html_blocks:
            processed_info.append("HTML:")
            for html in html_blocks:
                processed_info.append(f"{html}")
        
        if css_blocks:
            processed_info.append("\nCSS:")
            for css in css_blocks:
                processed_info.append(f"{css}")
        
        if js_blocks:
            processed_info.append("\nJavaScript:")
            for js in js_blocks:
                processed_info.append(f"{js}")
    
    return "\n".join(processed_info)

    pass