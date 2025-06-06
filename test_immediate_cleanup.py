#!/usr/bin/env python3
"""
Test simple pour créer un fichier avec des marqueurs Markdown et vérifier le nettoyage.
"""
import tempfile
import os
from pathlib import Path
from src.mcp.simple_validation_system import clean_markdown_artifacts

def test_immediate_cleanup():
    """Test le nettoyage immédiat après création de fichier."""
    
    # Simuler un fichier JavaScript généré avec marqueurs
    js_content_with_markers = '''```javascript
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
```'''

    # Créer un répertoire temporaire
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir)
        
        # Créer le fichier avec marqueurs (simule l'écriture par parse_and_write_code)
        js_file = test_path / "server.js"
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_content_with_markers)
        
        print("📁 Fichier créé avec marqueurs:")
        print(f"   {js_file}")
        
        # Vérifier le contenu avant nettoyage
        with open(js_file, 'r', encoding='utf-8') as f:
            content_before = f.read()
        
        print(f"🔍 Contenu AVANT nettoyage:")
        print(f"   Commence par: '{content_before[:15]}...'")
        print(f"   Se termine par: '...{content_before[-15:]}'")
        
        # Lancer le nettoyage (simule l'étape ajoutée dans generation_flow.py)
        print("\n🧹 Lancement du nettoyage...")
        cleaned_count = clean_markdown_artifacts(temp_dir)
        
        # Vérifier le contenu après nettoyage
        with open(js_file, 'r', encoding='utf-8') as f:
            content_after = f.read()
        
        print(f"✅ {cleaned_count} fichier(s) nettoyé(s)")
        print(f"🔍 Contenu APRÈS nettoyage:")
        print(f"   Commence par: '{content_after[:15]}...'")
        print(f"   Se termine par: '...{content_after[-15:]}'")
        
        # Vérifier que les marqueurs ont été supprimés
        if not content_after.startswith('```') and not content_after.endswith('```'):
            print("🚀 SUCCÈS: Les marqueurs Markdown ont été supprimés!")
            print("🎯 Le fichier peut maintenant être exécuté sans erreur.")
            return True
        else:
            print("❌ ÉCHEC: Les marqueurs sont toujours présents.")
            return False

if __name__ == "__main__":
    print("🧪 Test du nettoyage immédiat des marqueurs Markdown")
    print("=" * 55)
    test_immediate_cleanup()
