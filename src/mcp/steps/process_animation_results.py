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

from src.config.frontend_resources import ANIMATION_RESOURCES
"""
Traite les résultats des animations MCP.
"""
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
<link href="https://cdnjs.cloudflare.com/ajax/libs/hover.css/2.3.1/css/hover-min.css" rel="stylesheet">
<button class="hvr-grow">Hover to Grow</button>
<div class="hvr-float">Hover to Float</div>

CSS:
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
        """)
    elif animation_type.lower() in ['scroll', 'scrolling']:
        processed_info.append("\n### AOS (Animate On Scroll) Example ###")
        processed_info.append("""
HTML:
<link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>

<div data-aos="fade-up">Fade up on scroll</div>
<div data-aos="fade-down">Fade down on scroll</div>
<div data-aos="zoom-in" data-aos-delay="100">Zoom in with delay</div>

JavaScript:
// Initialize AOS
document.addEventListener('DOMContentLoaded', function() {
  AOS.init({
    duration: 800,
    easing: 'ease-in-out',
    once: true
  });
});
        """)
    
    return "\n".join(processed_info)