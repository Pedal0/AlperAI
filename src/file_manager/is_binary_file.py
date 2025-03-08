import os

def is_binary_file(file_path):
    """Check if a file is likely to be binary rather than text"""
    binary_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.ico', '.pdf', '.zip', '.tar', 
                         '.gz', '.exe', '.dll', '.so', '.pyc', '.ttf', '.woff']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in binary_extensions
