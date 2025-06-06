#!/usr/bin/env python3
"""
Test pour vérifier que le nettoyage fonctionne après les corrections automatiques.
"""
import tempfile
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_post_fix_cleanup():
    """
    Teste que les marqueurs markdown sont supprimés après les corrections automatiques.
    """
    print("🧪 Test du nettoyage après corrections automatiques")
    print("=" * 60)
    
    # Créer un répertoire temporaire
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Fichiers de test créés dans: {temp_dir}")
        
        # Créer des fichiers "corrigés" avec des marqueurs markdown
        test_files = {
            "corrected.js": """```javascript
console.log("Hello World");
function test() {
    return true;
}
```""",
            "fixed.py": """```python
def hello():
    print("Hello World")
    return "success"
```""",
            "repaired.css": """```css
.container {
    display: flex;
    justify-content: center;
}
```""",
            "clean_already.html": """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""
        }
        
        # Écrire les fichiers
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"📝 {len(test_files)} fichiers de test créés")
        
        # Simuler l'application des corrections avec nettoyage automatique
        from src.mcp.simple_validation_system import clean_markdown_artifacts
        
        print("🧹 Lancement du nettoyage post-correction...")
        cleaned_count = clean_markdown_artifacts(temp_dir)
        
        print(f"✅ {cleaned_count} fichiers nettoyés")
        
        # Vérifier que les fichiers sont propres
        success_count = 0
        for filename in test_files.keys():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Vérifier qu'il n'y a plus de marqueurs markdown
            if not content.startswith('```') and not content.endswith('```'):
                print(f"✅ {filename}: Propre après correction")
                success_count += 1
            else:
                print(f"❌ {filename}: Contient encore des marqueurs markdown")
                print(f"   Contenu: {content[:100]}...")
        
        print(f"\n🎯 Résultat: {success_count}/{len(test_files)} fichiers correctement nettoyés après correction")
        
        if success_count == len(test_files):
            print("🚀 SUCCÈS: Le nettoyage post-correction fonctionne parfaitement!")
            return True
        else:
            print("❌ ÉCHEC: Des marqueurs markdown persistent après correction")
            return False

if __name__ == "__main__":
    success = test_post_fix_cleanup()
    exit(0 if success else 1)
