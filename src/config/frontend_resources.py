"""
Frontend resources configuration module.
Contains links and resources for frontend components and libraries.
"""

# Popular UI libraries and frameworks
UI_LIBRARIES = {
    "bootstrap": {
        "name": "Bootstrap",
        "description": "Popular responsive CSS framework",
        "url": "https://getbootstrap.com/",
        "docs": "https://getbootstrap.com/docs/",
        "cdn": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css",
        "github": "https://github.com/twbs/bootstrap"
    },
    "tailwind": {
        "name": "Tailwind CSS",
        "description": "Utility-first CSS framework",
        "url": "https://tailwindcss.com/",
        "docs": "https://tailwindcss.com/docs",
        "cdn": "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
        "github": "https://github.com/tailwindlabs/tailwindcss"
    },
    "bulma": {
        "name": "Bulma",
        "description": "Modern CSS framework based on Flexbox",
        "url": "https://bulma.io/",
        "docs": "https://bulma.io/documentation/",
        "cdn": "https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css",
        "github": "https://github.com/jgthms/bulma"
    },
    "material": {
        "name": "Material Design",
        "description": "Google's Material Design implementation",
        "url": "https://material.io/",
        "docs": "https://material.io/develop/web/",
        "cdn": "https://unpkg.com/material-components-web@latest/dist/material-components-web.min.css",
        "github": "https://github.com/material-components/material-components-web"
    }
}

# Component libraries with code snippets
COMPONENT_LIBRARIES = {
    "navbar": {
        "description": "Navigation bar components",
        "sources": [
            "https://getbootstrap.com/docs/5.3/components/navbar/",
            "https://tailwindui.com/components/application-ui/navigation/navbars",
            "https://bulma.io/documentation/components/navbar/"
        ]
    },
    "card": {
        "description": "Card UI components",
        "sources": [
            "https://getbootstrap.com/docs/5.3/components/card/",
            "https://tailwindui.com/components/application-ui/layout/panels",
            "https://bulma.io/documentation/components/card/"
        ]
    },
    "form": {
        "description": "Form components and validation",
        "sources": [
            "https://getbootstrap.com/docs/5.3/forms/overview/",
            "https://tailwindui.com/components/application-ui/forms/form-layouts",
            "https://bulma.io/documentation/form/general/"
        ]
    },
    "button": {
        "description": "Button components and styles",
        "sources": [
            "https://getbootstrap.com/docs/5.3/components/buttons/",
            "https://tailwindui.com/components/application-ui/elements/buttons",
            "https://bulma.io/documentation/elements/button/"
        ]
    },
    "modal": {
        "description": "Modal dialog components",
        "sources": [
            "https://getbootstrap.com/docs/5.3/components/modal/",
            "https://tailwindui.com/components/application-ui/overlays/modals",
            "https://bulma.io/documentation/components/modal/"
        ]
    },
    "table": {
        "description": "Table components and data display",
        "sources": [
            "https://getbootstrap.com/docs/5.3/content/tables/",
            "https://tailwindui.com/components/application-ui/lists/tables",
            "https://bulma.io/documentation/elements/table/"
        ]
    }
}

# CSS animation resources
ANIMATION_RESOURCES = {
    "animate.css": {
        "name": "Animate.css",
        "description": "Cross-browser CSS animations library",
        "url": "https://animate.style/",
        "cdn": "https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css",
        "github": "https://github.com/animate-css/animate.css"
    },
    "hover.css": {
        "name": "Hover.css",
        "description": "CSS3 hover effects",
        "url": "https://ianlunn.github.io/Hover/",
        "cdn": "https://cdnjs.cloudflare.com/ajax/libs/hover.css/2.3.1/css/hover-min.css",
        "github": "https://github.com/IanLunn/Hover"
    },
    "aos": {
        "name": "AOS",
        "description": "Animate On Scroll library",
        "url": "https://michalsnik.github.io/aos/",
        "cdn": "https://unpkg.com/aos@2.3.1/dist/aos.css",
        "github": "https://github.com/michalsnik/aos"
    }
}

# Template websites for inspiration
TEMPLATE_WEBSITES = {
    "portfolio": [
        "https://onepagelove.com/tag/portfolio",
        "https://www.awwwards.com/websites/portfolio/",
        "https://www.creative-tim.com/templates/portfolio"
    ],
    "landing": [
        "https://onepagelove.com/tag/landing-page",
        "https://www.awwwards.com/websites/landing-page/",
        "https://www.creative-tim.com/templates/landing"
    ],
    "dashboard": [
        "https://www.creative-tim.com/templates/admin",
        "https://adminlte.io/",
        "https://demos.creative-tim.com/material-dashboard/examples/dashboard.html"
    ],
    "ecommerce": [
        "https://www.creative-tim.com/templates/e-commerce",
        "https://mdbootstrap.com/freebies/e-commerce/",
        "https://colorlib.com/wp/free-bootstrap-ecommerce-website-templates/"
    ]
}

# Best practices resources
BEST_PRACTICES = {
    "accessibility": "https://web.dev/learn/accessibility/",
    "performance": "https://web.dev/learn/performance/",
    "responsive": "https://web.dev/learn/design/",
    "seo": "https://web.dev/learn/seo/"
}

def get_component_sources(component_type, framework=None):
    """
    Get sources for a specific component type and optionally filtered by framework.
    
    Args:
        component_type (str): Type of component to look for
        framework (str, optional): Framework to filter by
        
    Returns:
        list: List of source URLs
    """
    if component_type not in COMPONENT_LIBRARIES:
        return []
    
    sources = COMPONENT_LIBRARIES[component_type]["sources"]
    
    if framework:
        # Filter sources by framework
        framework_lower = framework.lower()
        return [src for src in sources if framework_lower in src.lower()]
    
    return sources

def get_library_info(library_name):
    """
    Get information about a UI library.
    
    Args:
        library_name (str): Name of the library
        
    Returns:
        dict: Library information or None if not found
    """
    library_name_lower = library_name.lower()
    
    for key, info in UI_LIBRARIES.items():
        if key == library_name_lower or library_name_lower in info["name"].lower():
            return info
    
    return None

def get_animation_resource(name):
    """
    Get information about an animation resource.
    
    Args:
        name (str): Name of the animation resource
        
    Returns:
        dict: Animation resource information or None if not found
    """
    name_lower = name.lower()
    
    for key, info in ANIMATION_RESOURCES.items():
        if key == name_lower or name_lower in info["name"].lower():
            return info
    
    return None

def get_templates_by_type(template_type):
    """
    Get template website links by type.
    
    Args:
        template_type (str): Type of template (portfolio, landing, dashboard, etc.)
        
    Returns:
        list: List of template website URLs
    """
    template_type_lower = template_type.lower()
    
    for key, urls in TEMPLATE_WEBSITES.items():
        if key == template_type_lower:
            return urls
    
    # If no exact match, return first category as default
    return next(iter(TEMPLATE_WEBSITES.values()), [])
