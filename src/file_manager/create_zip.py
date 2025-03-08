import os

def create_zip(directory):
    """Create a ZIP archive of the directory"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(
                    file_path, 
                    os.path.relpath(file_path, os.path.join(directory, '..'))
                )
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

