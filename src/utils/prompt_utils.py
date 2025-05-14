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
Utility functions for prompt handling and detection.
"""
import re
import asyncio

def prompt_mentions_design(prompt_text):
    """
    Check if the user prompt mentions design-related terms.
    
    Args:
        prompt_text (str): The prompt text to analyze
        
    Returns:
        bool: True if design terms are mentioned, False otherwise
    """
    if not prompt_text:
        return False
        
    keywords = [
        "design", "style", "css", "layout", "look", "feel", "appearance",
        "minimalist", "modern", "bootstrap", "tailwind", "material",
        "theme", "color", "font", "ui", "ux", "interface", "visual",
        "animation", "transition"
    ]
    prompt_lower = prompt_text.lower()
    for keyword in keywords:
        if keyword in prompt_lower:
            return True
    return False

def extract_urls_from_prompt(prompt_text):
    """
    Extract URLs from the user prompt.
    
    Args:
        prompt_text (str): The prompt text to analyze
        
    Returns:
        list: List of extracted URLs
    """
    if not prompt_text:
        return []
    
    # Use regex to find URLs in the text
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+\.[^\s<>"\']+'
    found_urls = re.findall(url_pattern, prompt_text)
    
    # Ensure all URLs have proper scheme
    normalized_urls = []
    for url in found_urls:
        if url.startswith('www.'):
            normalized_urls.append('http://' + url)
        else:
            normalized_urls.append(url)
    
    return normalized_urls

async def fetch_url_content(url):
    """
    Fetch content from a URL asynchronously.
    
    Args:
        url (str): URL to fetch
        
    Returns:
        str: Fetched content or error message
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    content = await response.text()
                    # Truncate content if too large (to avoid token limits)
                    if len(content) > 15000:
                        content = content[:15000] + "... [content truncated due to length]"
                    return content
                else:
                    return f"Error fetching URL: HTTP status {response.status}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

async def process_urls(urls):
    """
    Process multiple URLs and fetch their content.
    
    Args:
        urls (list): List of URLs to process
        
    Returns:
        dict: Dictionary mapping URLs to their content
    """
    url_contents = {}
    
    # Limit to first 3 URLs to avoid token limits and long processing times
    for url in urls[:3]:
        content = await fetch_url_content(url)
        url_contents[url] = content
    
    return url_contents
