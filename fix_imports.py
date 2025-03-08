import os
import re

def fix_imports_in_functions_dir():
    functions_dir = 'src/validators/functions'
    
    # List of files in the parent directory that might be imported
    parent_modules = [
        'environment_setup', 'app_runner', 'dependency_detector', 
        'requirements_cleaner', 'entry_point_finder', 'error_fixer'
    ]
    
    for filename in os.listdir(functions_dir):
        if not filename.endswith('.py'):
            continue
            
        filepath = os.path.join(functions_dir, filename)
        with open(filepath, 'r') as file:
            content = file.read()
        
        # Replace imports from parent directory
        for module in parent_modules:
            # Change "from .module_name import" to "from ..module_name import"
            content = re.sub(
                f"from \\.{module} import", 
                f"from ..{module} import", 
                content
            )
        
        # Write the fixed content back
        with open(filepath, 'w') as file:
            file.write(content)
        
        print(f"Fixed imports in {filename}")

if __name__ == "__main__":
    fix_imports_in_functions_dir()