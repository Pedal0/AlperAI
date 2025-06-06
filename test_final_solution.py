#!/usr/bin/env python3
"""
Test final de vérification que le problème des marqueurs markdown est complètement résolu.
Simule un scénario réel avec génération + corrections automatiques + nettoyages.
"""
import tempfile
import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
sys.path.insert(0, os.path.abspath('.'))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_real_world_scenario():
    """
    Test complet qui simule le scénario réel d'utilisation.
    """
    print("🚀 Test du scénario réel complet")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Test dans: {temp_dir}")
        
        try:
            from src.utils.file_utils import parse_and_write_code, clean_code_block
            from src.mcp.simple_validation_system import clean_markdown_artifacts, apply_simple_fixes
        except ImportError as e:
            print(f"❌ Erreur d'import: {e}")
            return False
        
        # SCÉNARIO 1: Code généré par l'IA avec des marqueurs markdown
        print("\n📝 SCÉNARIO 1: Code généré avec marqueurs markdown")
        
        ai_generated_response = """--- FILE: app.js ---
```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

--- FILE: package.json ---
```json
{
  "name": "my-app",
  "version": "1.0.0",
  "main": "app.js",
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

--- FILE: styles.css ---
```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}
```"""
        
        # Étape 1: Parser et écrire les fichiers (comme dans generation_flow.py)
        files_written, errors, incomplete = parse_and_write_code(temp_dir, ai_generated_response)
        
        print(f"✅ {len(files_written)} fichiers écrits")
        
        # Vérifier si des marqueurs persistent après parse_and_write_code
        markdown_detected = False
        for file_path in files_written:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.startswith('```') or content.endswith('```'):
                markdown_detected = True
                print(f"⚠️  Marqueurs détectés dans {Path(file_path).name}")
        
        if not markdown_detected:
            print("✅ Génération initiale: Aucun marqueur markdown restant")
        
        # Étape 2: Nettoyage post-génération (comme dans generation_flow.py ligne ~334)
        print("\n🧹 ÉTAPE 2: Nettoyage post-génération")
        cleanup_count = clean_markdown_artifacts(temp_dir)
        print(f"✅ {cleanup_count} fichiers nettoyés après génération")
        
        # SCÉNARIO 2: IA fait des corrections et réintroduit des marqueurs
        print("\n🔧 SCÉNARIO 2: IA fait des corrections (réintroduit des marqueurs)")
        
        # Simuler une réponse de correction de l'IA avec marqueurs
        ai_correction_response = """🔧 APPLY_FIXES
=== FIX_FILE: app.js ===
```javascript
const express = require('express');
const app = express();

// Ajout: middleware pour parsing JSON
app.use(express.json());

app.get('/', (req, res) => {
    res.send('Hello World!');
});

// Correction: utiliser PORT depuis env
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
```
=== END_FIX ===

=== FIX_FILE: package.json ===
```json
{
  "name": "my-app",
  "version": "1.0.0",
  "main": "app.js",
  "scripts": {
    "start": "node app.js"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
```
=== END_FIX ==="""
        
        # Appliquer les corrections (avec nettoyage automatique intégré)
        fixes_applied = apply_simple_fixes(temp_dir, ai_correction_response)
        print(f"✅ {fixes_applied} corrections appliquées")
        
        # VÉRIFICATION FINALE: S'assurer qu'aucun marqueur ne persiste
        print("\n🔍 VÉRIFICATION FINALE")
        
        final_check_success = True
        corrected_content_preserved = True
        
        for file_path in Path(temp_dir).rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.js', '.json', '.css', '.py', '.html']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Vérifier l'absence de marqueurs markdown
                if content.startswith('```') or content.endswith('```') or '```' in content:
                    print(f"❌ Marqueurs markdown persistants dans {file_path.name}")
                    print(f"   Début: {content[:100]}...")
                    final_check_success = False
                else:
                    print(f"✅ {file_path.name}: Propre")
                
                # Vérifier que les corrections sont préservées
                if file_path.name == 'app.js':
                    if 'process.env.PORT' in content and 'express.json()' in content:
                        print(f"   ✓ Corrections préservées dans {file_path.name}")
                    else:
                        corrected_content_preserved = False
                        print(f"   ⚠️  Corrections perdues dans {file_path.name}")
        
        # RÉSULTAT FINAL
        print(f"\n🎯 RÉSULTAT FINAL:")
        
        if final_check_success and corrected_content_preserved:
            print("🚀 SUCCÈS COMPLET!")
            print("✅ Aucun marqueur markdown ne persiste")
            print("✅ Toutes les corrections sont préservées")
            print("✅ Le système de nettoyage fonctionne parfaitement")
            print("")
            print("🎉 PROBLÈME RÉSOLU: Les marqueurs markdown seront automatiquement")
            print("   supprimés après CHAQUE phase de correction de l'IA!")
            return True
        else:
            print("❌ ÉCHEC:")
            if not final_check_success:
                print("   • Des marqueurs markdown persistent")
            if not corrected_content_preserved:
                print("   • Des corrections ont été perdues")
            return False

if __name__ == "__main__":
    success = test_real_world_scenario()
    exit(0 if success else 1)
