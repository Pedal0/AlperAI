"""
SVG detector and generator module.

This module detects SVG references in generated code files and automatically
creates the corresponding SVG files.
"""

import os
import re
import json
from src.api.openrouter import generate_text
from src.config.constants import PRECISE_TEMPERATURE

class SVGDetector:
    """Detector for SVG references in code files and generator for missing SVG files."""
    
    def __init__(self, output_dir):
        """
        Initialize the SVG detector.
        
        Args:
            output_dir (str): Path to the project's output directory
        """
        self.output_dir = output_dir
        self.detected_svgs = {}  # Format: {filepath: {name, description, references}}
    
    def scan_file_for_svg_references(self, file_path):
        """
        Scan a single file for SVG references.
        
        Args:
            file_path (str): Path to the file to scan
            
        Returns:
            list: List of detected SVG references
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Get file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Different patterns based on file type
            svg_references = []
            
            if ext == '.html':
                # Look for <img> tags with .svg in src
                img_pattern = r'<img[^>]*src=["\'](.*?\.svg)["\'][^>]*>'
                svg_references.extend(re.findall(img_pattern, content))
                
                # Look for SVG references in background images
                style_pattern = r'style=["\'](.*?url\(["\']?(.*?\.svg)["\']?\))["\']'
                svg_references.extend(re.findall(style_pattern, content)[1] 
                                      if re.findall(style_pattern, content) else [])
                
            elif ext == '.css':
                # Look for background-image with .svg
                bg_pattern = r'background(?:-image)?:\s*url\(["\']?(.*?\.svg)["\']?\)'
                svg_references.extend(re.findall(bg_pattern, content))
                
                # Look for mask-image with .svg
                mask_pattern = r'(?:-webkit-)?mask-image:\s*url\(["\']?(.*?\.svg)["\']?\)'
                svg_references.extend(re.findall(mask_pattern, content))
                
            elif ext == '.js':
                # Look for string literals containing .svg
                js_pattern = r'["\']([^"\']*?\.svg)["\']'
                svg_references.extend(re.findall(js_pattern, content))
            
            # Process and normalize the references
            normalized_refs = []
            for ref in svg_references:
                # Remove query params and hashes
                ref = ref.split('?')[0].split('#')[0]
                
                # Skip data URIs
                if ref.startswith('data:'):
                    continue
                    
                # Skip absolute URLs to external resources
                if ref.startswith('http://') or ref.startswith('https://'):
                    continue
                    
                normalized_refs.append(ref)
            
            return normalized_refs
            
        except Exception as e:
            print(f"Error scanning {file_path} for SVG references: {str(e)}")
            return []
    
    def scan_project_for_svg_references(self):
        """
        Scan the entire project for SVG references.
        
        Returns:
            dict: Dictionary of detected SVG references
        """
        self.detected_svgs = {}
        
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Only scan HTML, CSS, and JS files
                if ext not in ['.html', '.css', '.js']:
                    continue
                    
                # Skip files in node_modules, .git, etc.
                if any(ignore in root for ignore in ['node_modules', '.git', '__pycache__']):
                    continue
                
                # Scan file for SVG references
                references = self.scan_file_for_svg_references(file_path)
                
                # Process and store each reference
                for ref in references:
                    # Normalize path
                    if ref.startswith('/'):
                        svg_path = ref[1:]  # Remove leading slash
                    else:
                        # Get relative path from the file to the reference
                        referencing_dir = os.path.dirname(os.path.relpath(file_path, self.output_dir))
                        svg_path = os.path.normpath(os.path.join(referencing_dir, ref))
                    
                    # Get svg name for description
                    svg_name = os.path.basename(svg_path)
                    svg_name_without_ext = os.path.splitext(svg_name)[0]
                    
                    # Clean up name for better descriptions
                    clean_name = svg_name_without_ext.replace('-', ' ').replace('_', ' ')
                    if clean_name.startswith('icon '):
                        clean_name = clean_name[5:]  # Remove 'icon ' prefix
                    
                    # Add to detected SVGs
                    if svg_path not in self.detected_svgs:
                        self.detected_svgs[svg_path] = {
                            'name': clean_name,
                            'description': f"{clean_name} icon",
                            'references': [file_path]
                        }
                    else:
                        self.detected_svgs[svg_path]['references'].append(file_path)
        
        print(f"Found {len(self.detected_svgs)} SVG references in the project")
        return self.detected_svgs
    
    def generate_svg_files(self):
        """
        Generate all detected SVG files.
        
        Returns:
            list: List of paths to generated SVG files
        """
        generated_files = []
        
        for svg_path, info in self.detected_svgs.items():
            try:
                # Create full path
                full_path = os.path.join(self.output_dir, svg_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Generate SVG content
                svg_content = self.generate_svg_content(info['name'], info['description'])
                
                # Write SVG file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                generated_files.append(full_path)
                print(f"Generated SVG file: {svg_path}")
                
            except Exception as e:
                print(f"Error generating SVG file {svg_path}: {str(e)}")
        
        return generated_files
    
    def generate_svg_content(self, icon_name, description=None):
        """
        Generate SVG content for a given icon name.
        
        Args:
            icon_name (str): Name of the icon to generate
            description (str, optional): Description of the icon
            
        Returns:
            str: SVG content
        """
        if not description:
            description = f"{icon_name} icon"
        
        # Create system message
        system_message = """
        You are an expert SVG icon designer. Your task is to create clean, 
        scalable SVG icons for web use. Each icon should be simple, 
        professional, and optimized.
        
        Generate ONLY the SVG markup - no explanations, no code block markers.
        """
        
        # Create prompt
        prompt = f"""
        Create a clean, optimized SVG icon for "{icon_name}".
        
        Description: {description}
        
        Requirements:
        1. Use a 24x24 viewBox
        2. Keep it simple and recognizable even at small sizes
        3. Use minimal number of paths and shapes
        4. Use currentColor for stroke/fill to allow styling via CSS
        5. Include appropriate viewBox, width, and height attributes
        6. Ensure the icon is visible and properly centered
        7. Optimize SVG code by removing unnecessary elements
        8. Return ONLY the SVG code (no markdown, no explanations)
        """
        
        # Generate SVG content
        svg_content = generate_text(
            prompt=prompt,
            temperature=PRECISE_TEMPERATURE,
            system_message=system_message
        )
        
        # Clean up the content
        svg_content = self._clean_svg_content(svg_content, icon_name)
        
        return svg_content
    
    def _clean_svg_content(self, content, icon_name):
        """
        Clean and optimize SVG content.
        
        Args:
            content (str): Raw SVG content
            icon_name (str): Name of the icon
            
        Returns:
            str: Cleaned SVG content
        """
        # Extract the SVG content if wrapped in code block
        if "```" in content:
            match = re.search(r"```(?:svg|xml)?\s*([\s\S]+?)\s*```", content)
            if match:
                content = match.group(1)
        
        # Ensure it starts with <svg
        if not content.strip().startswith('<svg'):
            # Try to extract just the SVG tag and its content
            match = re.search(r"(<svg[^>]*>[\s\S]*</svg>)", content)
            if match:
                content = match.group(1)
        
        # Ensure viewBox attribute
        if "viewBox" not in content:
            content = content.replace('<svg', '<svg viewBox="0 0 24 24"')
        
        # Ensure width and height
        if "width=" not in content:
            content = content.replace('<svg', '<svg width="24"')
        
        if "height=" not in content:
            content = content.replace('<svg', '<svg height="24"')
        
        # Ensure fill/stroke uses currentColor
        if "currentColor" not in content:
            if "fill=" not in content and "stroke=" not in content:
                content = content.replace('<svg', '<svg fill="currentColor"')
            else:
                # Replace explicit colors with currentColor
                content = re.sub(r'fill="(?!none)([^"]*)"', 'fill="currentColor"', content)
                content = re.sub(r'stroke="(?!none)([^"]*)"', 'stroke="currentColor"', content)
        
        # Add a comment with the icon name
        content = f"<!-- {icon_name} icon -->\n{content}"
        
        return content
