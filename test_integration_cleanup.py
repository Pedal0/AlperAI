#!/usr/bin/env python3
"""
Test d'intégration finale pour vérifier que tous les points de nettoyage fonctionnent.
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

def test_integration_complete():
    """
    Test d'intégration finale : tous les points de nettoyage.
    """
    print("🧪 Test d'intégration finale - Tous les points de nettoyage")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Répertoire de test: {temp_dir}")
        
        # Importer les modules nécessaires
        try:
            from src.mcp.simple_validation_system import (
                clean_markdown_artifacts, 
                apply_simple_fixes,
                validate_and_fix_with_repomix
            )
            from src.utils.file_utils import clean_code_block
        except ImportError as e:
            print(f"❌ Erreur d'import: {e}")
            return False
          # POINT 1: Test du nettoyage immédiat (file_utils.clean_code_block)
        print("\n🧹 POINT 1: Nettoyage immédiat dans file_utils")
        
        test_content = """```javascript
console.log("Test");
```"""
        
        cleaned_content = clean_code_block(test_content)
        if not cleaned_content.startswith('```'):
            print("✅ Point 1: Nettoyage immédiat OK")
            point1_success = True
        else:
            print("❌ Point 1: Nettoyage immédiat ÉCHEC")
            point1_success = False
        
        # POINT 2: Test du nettoyage post-génération
        print("\n🧹 POINT 2: Nettoyage post-génération")
        
        # Créer des fichiers avec marqueurs
        test_files = {
            "generated1.js": "```javascript\nconsole.log('generated');\n```",
            "generated2.py": "```python\nprint('test')\n```"
        }
        
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        cleanup_count = clean_markdown_artifacts(temp_dir)
        if cleanup_count == 2:
            print("✅ Point 2: Nettoyage post-génération OK")
            point2_success = True
        else:
            print(f"❌ Point 2: Nettoyage post-génération ÉCHEC ({cleanup_count}/2)")
            point2_success = False
        
        # POINT 3: Test du nettoyage dans apply_simple_fixes
        print("\n🧹 POINT 3: Nettoyage dans apply_simple_fixes")
        
        # Simuler une réponse IA avec corrections
        mock_ai_response = """🔧 APPLY_FIXES
=== FIX_FILE: corrected.js ===
```javascript
function fixed() {
    return "corrected";
}
```
=== END_FIX ==="""
        
        fixes_applied = apply_simple_fixes(temp_dir, mock_ai_response)
        
        # Vérifier que le fichier corrigé est propre
        corrected_file = Path(temp_dir) / "corrected.js"
        if corrected_file.exists():
            with open(corrected_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.startswith('```') and fixes_applied > 0:
                print("✅ Point 3: Nettoyage dans apply_simple_fixes OK")
                point3_success = True
            else:
                print(f"❌ Point 3: Nettoyage dans apply_simple_fixes ÉCHEC")
                print(f"   Contenu: {content[:100]}...")
                point3_success = False
        else:
            print("❌ Point 3: Fichier corrigé non créé")
            point3_success = False
        
        # Résultat final
        print(f"\n🎯 RÉSULTATS:")
        print(f"   Point 1 (nettoyage immédiat): {'✅' if point1_success else '❌'}")
        print(f"   Point 2 (post-génération): {'✅' if point2_success else '❌'}")
        print(f"   Point 3 (post-correction): {'✅' if point3_success else '❌'}")
        
        all_success = point1_success and point2_success and point3_success
        
        if all_success:
            print("\n🚀 INTÉGRATION COMPLÈTE RÉUSSIE!")
            print("✅ Tous les points de nettoyage fonctionnent correctement")
            print("✅ Les marqueurs markdown seront supprimés à tous les moments critiques")
            return True
        else:
            print("\n❌ INTÉGRATION INCOMPLÈTE")
            print("⚠️  Certains points de nettoyage ne fonctionnent pas")
            return False

if __name__ == "__main__":
    success = test_integration_complete()
    exit(0 if success else 1)
