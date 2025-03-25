import os
import logging
from pathlib import Path
import re
import base64

logger = logging.getLogger(__name__)

class SVGIconGenerator:
    """
    A generator for inline SVG icons to be used in web applications.
    Only generates SVG markup for inline embedding - does NOT create SVG files.
    The preferred method is to embed SVG icons directly in CSS.
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
        Generate SVG markup for inline use only - does NOT create files.
        
        Args:
            icon_name (str): The name of the icon to generate
            icon_description (str): A description of what the icon represents
            app_type (str): The type of application the icon will be used in
            
        Returns:
            str: The SVG markup for the requested icon (for inline use only)
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
        
        # Add explicit instructions for better SVGs and to ensure inline-only usage
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
        9. ONLY CREATE INLINE SVG CODE - this will NOT be saved as a separate file
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
        COMPLETELY DISABLED - No SVG files will be generated.
        This method now explicitly logs a warning and returns an empty list.
        
        Args:
            project_path (str): Ignored
            icon_definitions (list): Ignored
        
        Returns:
            list: Empty list as no files are generated
        """
        logger.warning(
            "SVG file generation is explicitly disabled. No SVG files will be created. "
            "For icons, use inline SVG via get_inline_svg_content() method instead."
        )
        return []
    
    def _clean_svg_content(self, svg_content):
        """
        Clean and optimize the SVG content for inline use.
        
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
        shape_elements = ['path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse', 'text']
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
            str: A simple placeholder SVG for inline use
        """
        first_char = icon_name[0].upper() if icon_name else "I"
        
        return f"""<!-- Placeholder for {icon_name} icon (inline use only) -->
<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"></circle>
  <text x="12" y="16" text-anchor="middle" fill="currentColor" font-size="12">{first_char}</text>
</svg>"""

    def get_inline_svg_content(self, icon_name, icon_description=None, app_type="web"):
        """
        Get SVG content for inline embedding directly in HTML/JS/CSS files.
        This is the ONLY supported method for using SVG icons.
        
        Args:
            icon_name (str): The name of the icon to generate
            icon_description (str): A description of what the icon represents
            app_type (str): The type of application the icon will be used in
            
        Returns:
            str: The SVG markup for the requested icon (optimized for inline use)
        """
        svg_content = self.generate_svg_icon(icon_name, icon_description, app_type)
        
        # Optimize the SVG for inline usage
        # Strip any XML declarations or doctype
        svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
        svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
        
        # Minify by removing unnecessary whitespace
        svg_content = re.sub(r'>\s+<', '><', svg_content)
        svg_content = re.sub(r'\s{2,}', ' ', svg_content)
        
        # Add comment to clarify this is for inline use only
        if '<!--' not in svg_content:
            svg_content = f"<!-- {icon_name} icon (inline use only) -->\n{svg_content}"
        
        return svg_content.strip()
    
    def get_css_svg_content(self, icon_name, icon_description=None, app_type="web", as_data_uri=False):
        """
        Get SVG content formatted for embedding directly in CSS files.
        This is the PREFERRED method for using SVG icons in the application.
        
        Args:
            icon_name (str): The name of the icon to generate
            icon_description (str): A description of what the icon represents
            app_type (str): The type of application the icon will be used in
            as_data_uri (bool): If True, returns a data URI format for background-image
                               If False, returns CSS for mask-image with the SVG embedded
            
        Returns:
            str: CSS code with the SVG content embedded
        """
        svg_content = self.generate_svg_icon(icon_name, icon_description, app_type)
        
        # Optimize the SVG for CSS usage
        svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
        svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
        svg_content = re.sub(r'>\s+<', '><', svg_content)
        svg_content = re.sub(r'\s{2,}', ' ', svg_content)
        svg_content = svg_content.strip()
        
        # Remove any existing comments
        svg_content = re.sub(r'<!--.*?-->', '', svg_content)
        
        if as_data_uri:
            # Encode as data URI for background-image
            # First, ensure the SVG is properly encoded for a URI
            svg_uri_encoded = svg_content.replace('#', '%23')
            svg_uri_encoded = svg_uri_encoded.replace('"', "'")
            
            css = f"""/* {icon_name} icon */
.icon-{icon_name.lower().replace(' ', '-')} {{
    background-image: url("data:image/svg+xml,{svg_uri_encoded}");
    background-position: center;
    background-repeat: no-repeat;
    background-size: contain;
}}"""
        else:
            # Use mask-image with embedded SVG (modern approach)
            css = f"""/* {icon_name} icon */
.icon-{icon_name.lower().replace(' ', '-')} {{
    mask-image: url('data:image/svg+xml,{svg_content.replace('"', "'")}');
    -webkit-mask-image: url('data:image/svg+xml,{svg_content.replace('"', "'")}');
    mask-size: cover;
    -webkit-mask-size: cover;
    mask-repeat: no-repeat;
    -webkit-mask-repeat: no-repeat;
    background-color: currentColor;
}}"""
            
        return css
    
    def generate_css_icon_library(self, icon_names):
        """
        Generate a complete CSS file with all requested icons embedded.
        This is the recommended way to include SVG icons in projects.
        
        Args:
            icon_names (list): List of icon names to include in the library
            
        Returns:
            str: Complete CSS content with all icons embedded
        """
        css_content = [
            "/* SVG Icon Library - Auto-generated */",
            "/* Use these classes with a div or span element */",
            "/* All icons use currentColor for coloring - inherit from parent */",
            ""
        ]
        
        for icon_name in icon_names:
            css_content.append(self.get_css_svg_content(icon_name))
            css_content.append("")
        
        # Add helper class for common styling
        css_content.append("""
/* Common icon styling */
.icon {
    display: inline-block;
    width: 24px;
    height: 24px;
    vertical-align: middle;
}
""")
        
        return "\n".join(css_content)
    
    def should_ignore_svg_file(self, file_path):
        """
        Check if an SVG file in the project structure should be ignored.
        
        Args:
            file_path (str): Path to the potential SVG file
            
        Returns:
            bool: True if the file is an SVG that should be ignored
        """
        # Check if this is an SVG file
        if file_path.lower().endswith('.svg'):
            logger.warning(f"SVG file detected and will be ignored: {file_path}. Use CSS-embedded SVG icons instead.")
            return True
        return False
    
    def get_svg_replacement_suggestion(self, svg_filename):
        """
        Generate a suggestion for replacing a SVG file reference with CSS-embedded SVG.
        Used by code reviewers to suggest better practices.
        
        Args:
            svg_filename (str): The name of the SVG file being referenced
            
        Returns:
            str: A suggestion for how to replace the SVG reference
        """
        icon_name = os.path.splitext(os.path.basename(svg_filename))[0]
        
        suggestion = f"""
SUGGESTION: Replace the reference to '{svg_filename}' with a CSS class:

1. Add this SVG to your CSS file using the SVGIconGenerator:
   ```
   {self.get_css_svg_content(icon_name)}
   ```

2. Replace the <img> tag with:
   ```html
   <span class="icon icon-{icon_name.lower().replace(' ', '-')}"></span>
   ```

3. Or for background image in CSS, replace:
   ```css
   background-image: url('{svg_filename}');
   ```
   with:
   ```css
   background-color: currentColor;
   mask-image: url('data:image/svg+xml,...'); /* Use the generator */
   -webkit-mask-image: url('data:image/svg+xml,...'); /* Use the generator */
   mask-size: cover;
   -webkit-mask-size: cover;
   ```
"""
        return suggestion
