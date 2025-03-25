import os
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class SVGIconGenerator:
    """
    A generator for SVG icons to be used in web applications.
    Creates standardized, accessible SVG icons based on provided specifications.
    """
    
    def __init__(self, ai_provider):
        """
        Initialize the SVG icon generator.
        
        Args:
            ai_provider: The AI provider used to generate SVG content
        """
        self.ai_provider = ai_provider
        
    def generate_svg_icon(self, icon_name, icon_description=None, app_type="web"):
        """
        Generate an SVG icon based on the provided name and description.
        
        Args:
            icon_name (str): The name of the icon to generate
            icon_description (str): A description of what the icon represents
            app_type (str): The type of application the icon will be used in
            
        Returns:
            str: The SVG markup for the requested icon
        """
        # If no description provided, create one from the name
        if not icon_description:
            icon_description = f"{icon_name} icon"
        
        # Enhanced prompt parameters to get better SVG results
        prompt_params = {
            "icon_name": icon_name,
            "icon_description": icon_description,
            "app_type": app_type
        }
        
        # Add specific guidance for common icons to improve results
        common_icons = {
            # Navigation icons
            "menu": "A hamburger menu icon with three horizontal lines",
            "home": "A house or home symbol with pitched roof and base",
            "back": "A left-pointing arrow or chevron",
            "forward": "A right-pointing arrow or chevron",
            "settings": "A gear or cog wheel icon with teeth around the perimeter",
            "logout": "A door with an exit arrow or power button symbol",
            
            # Action icons
            "search": "A magnifying glass icon with handle and circular lens",
            "add": "A plus sign icon for adding content",
            "delete": "A trash can or waste bin icon for deletion",
            "edit": "A pencil or pen icon for editing content",
            "save": "A floppy disk or downward arrow to cloud icon",
            "download": "A downward arrow into a horizontal line",
            "upload": "An upward arrow from a horizontal line",
            "close": "An X icon for closing or dismissing content",
            
            # Status icons
            "success": "A checkmark or tick icon",
            "error": "An X or exclamation mark in a circle",
            "warning": "An exclamation mark in a triangle",
            "info": "The letter 'i' in a circle",
            
            # User icons
            "user": "A simple user profile icon with head and shoulders silhouette",
            "profile": "A user silhouette or avatar placeholder",
            
            # Financial icons
            "income": "An upward trending arrow or dollar/currency symbol with upward indicator",
            "expense": "A downward trending arrow or dollar/currency symbol with downward indicator",
            "investment": "A growth chart with upward trend or money bag with chart",
            
            # Theme icons
            "sun": "A sun symbol with rays, representing light mode",
            "moon": "A crescent moon shape, representing dark mode",
            
            # Miscellaneous
            "expand": "Outward-pointing arrows or plus symbol",
            "collapse": "Inward-pointing arrows or minus symbol",
            "notification": "A bell icon",
            "calendar": "A calendar or date icon",
            "clock": "A clock or time icon"
        }
        
        # If we have a specific description for this icon, use it
        if icon_name.lower() in common_icons:
            prompt_params["icon_description"] = common_icons[icon_name.lower()]
        
        # Add explicit instructions for better SVGs
        prompt_params["additional_instructions"] = f"""
        IMPORTANT:
        1. Create a SIMPLE, clean SVG icon for '{icon_name}' that matches this description: {icon_description}
        2. Use a 24x24 viewBox
        3. Ensure the icon is visible and properly centered
        4. Use currentColor for stroke/fill to allow CSS styling
        5. Avoid complex gradients or effects
        6. Include only essential elements for recognition
        7. Use minimal paths and shapes
        8. The icon should look professional and consistent with standard icon sets
        """
        
        try:
            # Try up to 2 times to generate a good SVG
            for attempt in range(2):
                svg_content = self.ai_provider.generate_content("svg_icon", prompt_params)
                svg_content = self._clean_svg_content(svg_content)
                
                # Check if this is a valid SVG
                if self._is_valid_svg(svg_content):
                    return svg_content
                    
                # If invalid, add more specific instructions for the retry
                if attempt == 0:
                    prompt_params["additional_instructions"] += """
                    THE PREVIOUS SVG WAS INVALID. Please ensure:
                    1. The SVG begins with <svg and ends with </svg>
                    2. All tags are properly closed
                    3. The viewBox is properly defined (e.g., viewBox="0 0 24 24")
                    4. The icon contains visible elements (path, circle, rect, etc.)
                    """
            
            # If we still don't have a valid SVG, return a placeholder
            logger.warning(f"Failed to generate valid SVG for '{icon_name}' after 2 attempts")
            return self._generate_placeholder_svg(icon_name)
        except Exception as e:
            logger.error(f"Error generating SVG icon '{icon_name}': {e}")
            # Return a simple placeholder SVG if generation fails
            return self._generate_placeholder_svg(icon_name)
    
    def generate_icons_for_project(self, project_path, icon_definitions):
        """
        Generate multiple icons for a project and save them to the appropriate directory.
        
        Args:
            project_path (str): The root path of the project
            icon_definitions (list): List of dictionaries containing icon specifications
                                    Each dict should have 'name', 'file', and 'description' keys
        
        Returns:
            list: Paths to the generated icon files
        """
        if not icon_definitions:
            logger.warning("No icon definitions provided, skipping icon generation")
            return []
        
        # Create icons directory if it doesn't exist
        icons_dir = Path(project_path) / "assets" / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        logger.info(f"Generating {len(icon_definitions)} specific icons")
        
        for icon_def in icon_definitions:
            icon_name = icon_def.get("name", "")
            # Get the exact filename from the definition or construct it with the correct format
            icon_file = icon_def.get("file", "")
            if not icon_file:
                icon_file = f"{icon_name}.svg" if not icon_name.startswith("icon-") else f"{icon_name}.svg"
            
            if not icon_file.lower().endswith('.svg'):
                icon_file += '.svg'
                
            icon_description = icon_def.get("description", f"{icon_name} icon")
            
            try:
                logger.info(f"Generating icon: {icon_name} ({icon_file})")
                svg_content = self.generate_svg_icon(icon_name, icon_description)
                
                icon_path = icons_dir / icon_file
                
                with open(icon_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                generated_files.append(str(icon_path))
                logger.info(f"Generated icon: {icon_file}")
            except Exception as e:
                logger.error(f"Failed to generate icon '{icon_name}': {e}")
        
        return generated_files
    
    def _clean_svg_content(self, svg_content):
        """
        Clean and optimize the SVG content.
        
        Args:
            svg_content (str): The raw SVG content
            
        Returns:
            str: Cleaned and optimized SVG content
        """
        # Strip any non-SVG text that might have been generated
        if "<svg" in svg_content:
            start = svg_content.find("<svg")
            end = svg_content.rfind("</svg>") + 6
            if start >= 0 and end > start:
                svg_content = svg_content[start:end]
        
        # Ensure viewBox is present if not already
        if "viewBox=" not in svg_content and "<svg" in svg_content:
            svg_content = svg_content.replace("<svg", '<svg viewBox="0 0 24 24"')
        
        # Ensure fill or stroke uses currentColor for CSS styling
        if "currentColor" not in svg_content:
            # If there are explicit fill colors, replace them with currentColor
            svg_content = re.sub(r'fill="(?!none)([^"]*)"', 'fill="currentColor"', svg_content)
            svg_content = re.sub(r'stroke="(?!none)([^"]*)"', 'stroke="currentColor"', svg_content)
            
            # If no fill/stroke attributes were found, add fill to the SVG root
            if "fill=" not in svg_content and "stroke=" not in svg_content:
                svg_content = svg_content.replace("<svg", '<svg fill="currentColor"')
        
        # Remove XML declaration and DOCTYPE as they're not needed
        svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
        svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
        
        # Remove namespace declarations for simplicity if present
        svg_content = re.sub(r'xmlns:xlink="[^"]*"', '', svg_content)
        
        # Ensure width and height attributes for better browser compatibility if not already present
        if "width=" not in svg_content and "height=" not in svg_content:
            svg_content = svg_content.replace("<svg", '<svg width="24" height="24"')
            
        # Add a comment with the icon name at the top
        svg_parts = svg_content.split('<svg', 1)
        if len(svg_parts) > 1:
            svg_content = f"{svg_parts[0]}<!-- Icon: {svg_content.split('<svg', 1)[0].strip()} -->\n<svg{svg_parts[1]}"
        
        return svg_content
    
    def _is_valid_svg(self, svg_content):
        """
        Check if the generated SVG content is valid.
        
        Args:
            svg_content (str): The SVG content to validate
            
        Returns:
            bool: True if the SVG is valid, False otherwise
        """
        # Basic validation checks
        if not svg_content or len(svg_content) < 30:
            return False
            
        if '<svg' not in svg_content or '</svg>' not in svg_content:
            return False
            
        # Check for required attributes
        if 'viewBox=' not in svg_content:
            return False
            
        # Check for content within the SVG (at least one shape element)
        shape_elements = ['path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse']
        has_shape = any(f'<{shape}' in svg_content.lower() for shape in shape_elements)
        if not has_shape:
            return False
            
        # Check for common problems
        if 'width="0"' in svg_content or 'height="0"' in svg_content:
            return False
            
        return True
    
    def _generate_placeholder_svg(self, icon_name):
        """
        Generate a simple placeholder SVG when icon generation fails.
        
        Args:
            icon_name (str): The name of the icon
            
        Returns:
            str: A simple placeholder SVG
        """
        first_char = icon_name[0].upper() if icon_name else "I"
        
        return f"""<!-- Placeholder for {icon_name} icon -->
<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"></circle>
  <text x="12" y="16" text-anchor="middle" fill="currentColor" font-size="12">{first_char}</text>
</svg>"""
