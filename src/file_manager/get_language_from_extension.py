import os

def get_language_from_extension(file_path):
    """Determine the appropriate language for syntax highlighting based on file extension"""
    ext = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'bash',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.tsx': 'typescript',
        '.ts': 'typescript',
        '.jsx': 'javascript'
    }
    return language_map.get(ext, 'text')
