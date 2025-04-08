"""
Handlers for different MCP tools to process their results and integrate them into code generation.
"""
import re
import json
import streamlit as st
from src.config.frontend_resources import (
    get_component_sources,
    get_library_info,
    get_animation_resource,
    get_templates_by_type,
    UI_LIBRARIES,
    ANIMATION_RESOURCES,
    BEST_PRACTICES
)

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

def process_frontend_templates_results(template_results, template_type):
    """
    Process frontend template search results and add curated resources.
    
    Args:
        template_results (str): Raw template search results
        template_type (str): Type of template requested
        
    Returns:
        str: Processed template information with links to curated resources
    """
    processed_info = ["### Template Resources ###"]
    processed_info.append(template_results)
    
    # Add curated resources
    template_links = get_templates_by_type(template_type)
    if template_links:
        processed_info.append("\n### Curated Template Resources ###")
        processed_info.append(f"Template type: {template_type}")
        processed_info.append("Recommended resources:")
        for i, link in enumerate(template_links, 1):
            processed_info.append(f"{i}. {link}")
    
    return "\n".join(processed_info)

def process_animation_results(animation_results, animation_type):
    """
    Process animation resource search results and add curated resources.
    
    Args:
        animation_results (str): Raw animation search results
        animation_type (str): Type of animation requested
        
    Returns:
        str: Processed animation information with links to curated resources
    """
    processed_info = ["### Animation Resources ###"]
    processed_info.append(animation_results)
    
    # Add curated animation resources
    processed_info.append("\n### Curated Animation Libraries ###")
    for name, info in ANIMATION_RESOURCES.items():
        processed_info.append(f"\n{info['name']} - {info['description']}")
        processed_info.append(f"URL: {info['url']}")
        processed_info.append(f"CDN: {info['cdn']}")
    
    # Add code examples based on animation type
    if animation_type.lower() in ['hover', 'mouse']:
        processed_info.append("\n### Hover.css Example ###")
        processed_info.append("""
HTML:
```html
<link href="https://cdnjs.cloudflare.com/ajax/libs/hover.css/2.3.1/css/hover-min.css" rel="stylesheet">
<button class="hvr-grow">Hover to Grow</button>
<div class="hvr-float">Hover to Float</div>
```

CSS:
```css
/* Add to existing CSS if not using the CDN */
.hvr-grow {
  display: inline-block;
  vertical-align: middle;
  transform: translateZ(0);
  box-shadow: 0 0 1px rgba(0, 0, 0, 0);
  backface-visibility: hidden;
  -moz-osx-font-smoothing: grayscale;
  transition-duration: 0.3s;
  transition-property: transform;
}
.hvr-grow:hover,
.hvr-grow:focus,
.hvr-grow:active {
  transform: scale(1.1);
}
```
        """)
    elif animation_type.lower() in ['scroll', 'scrolling']:
        processed_info.append("\n### AOS (Animate On Scroll) Example ###")
        processed_info.append("""
HTML:
```html
<link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>

<div data-aos="fade-up">Fade up on scroll</div>
<div data-aos="fade-down">Fade down on scroll</div>
<div data-aos="zoom-in" data-aos-delay="100">Zoom in with delay</div>
```

JavaScript:
```javascript
// Initialize AOS
document.addEventListener('DOMContentLoaded', function() {
  AOS.init({
    duration: 800,
    easing: 'ease-in-out',
    once: true
  });
});
```
        """)
    
    return "\n".join(processed_info)

def handle_tool_results(tool_name, tool_results, tool_args=None):
    """
    Process tool results based on the specific tool that was used.
    
    Args:
        tool_name (str): The name of the tool that was executed
        tool_results (str): The raw results from the tool
        tool_args (dict, optional): The arguments used for the tool call
        
    Returns:
        str: Processed and formatted tool results
    """
    if tool_name == "web_search":
        return process_web_search_results(tool_results)
    
    elif tool_name == "search_documentation":
        return process_documentation_results(tool_results)
    
    elif tool_name == "search_frontend_components":
        # If we have args, add curated resources
        if tool_args and 'component_type' in tool_args and 'framework' in tool_args:
            component_type = tool_args['component_type']
            framework = tool_args['framework']
            
            # Get curated sources for this component and framework
            sources = get_component_sources(component_type, framework)
            
            # Get framework info
            framework_info = get_library_info(framework)
            
            # Prepare additional information to append
            additional_info = ["\n### Curated Component Resources ###"]
            if framework_info:
                additional_info.append(f"\n{framework_info['name']} Documentation: {framework_info['docs']}")
                additional_info.append(f"CDN: {framework_info['cdn']}")
            
            if sources:
                additional_info.append("\nComponent-specific resources:")
                for i, src in enumerate(sources, 1):
                    additional_info.append(f"{i}. {src}")
            
            # Process tool results normally first
            processed = process_frontend_component_results(tool_results)
            
            # Append curated resources
            return processed + "\n" + "\n".join(additional_info)
        else:
            return process_frontend_component_results(tool_results)
    
    elif tool_name == "search_frontend_templates":
        if tool_args and 'template_type' in tool_args:
            return process_frontend_templates_results(tool_results, tool_args['template_type'])
        return process_frontend_templates_results(tool_results, "general")
    
    elif tool_name == "search_animation_resources":
        if tool_args and 'animation_type' in tool_args:
            return process_animation_results(tool_results, tool_args['animation_type'])
        return process_animation_results(tool_results, "general")
    
    else:
        # Generic handling for unknown tools
        return f"### Results from {tool_name} ###\n{tool_results}"
