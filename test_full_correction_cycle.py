#!/usr/bin/env python3
"""
Test intégré pour simuler le problème exact mentionné:
1. Fichier généré correctement
2. IA fait des corrections et réintroduit des marqueurs markdown
3. Nettoyage automatique après correction
"""
import tempfile
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_full_correction_cycle():
    """
    Simule le cycle complet: génération -> correction IA -> nettoyage.
    """
    print("🧪 Test du cycle complet génération -> correction -> nettoyage")
    print("=" * 70)
    
    # Créer un répertoire temporaire
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Répertoire de test: {temp_dir}")
        
        # ÉTAPE 1: Simuler des fichiers générés correctement (sans marqueurs)
        print("\n📝 ÉTAPE 1: Génération initiale (fichiers propres)")
        initial_files = {
            "app.js": """console.log("Hello World");
function calculateSum(a, b) {
    return a + b;
}
export default calculateSum;""",
            
            "utils.py": """def process_data(data):
    if not data:
        return []
    return [item.upper() for item in data]

def validate_input(value):
    return value is not None and len(str(value)) > 0""",
            
            "styles.css": """body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}
.container {
    max-width: 800px;
    margin: 0 auto;
}"""
        }
        
        # Écrire les fichiers initiaux
        for filename, content in initial_files.items():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"✅ {len(initial_files)} fichiers générés proprement")
        
        # ÉTAPE 2: Simuler une correction par l'IA qui réintroduit des marqueurs
        print("\n🔧 ÉTAPE 2: IA fait des corrections et réintroduit des marqueurs markdown")
        
        # Simuler la fonction apply_simple_fixes avec du contenu "corrigé" par l'IA
        corrected_content = {
            "app.js": """```javascript
console.log("Hello World");
function calculateSum(a, b) {
    // Correction: Ajouter validation
    if (typeof a !== 'number' || typeof b !== 'number') {
        throw new Error('Parameters must be numbers');
    }
    return a + b;
}
export default calculateSum;
```""",
            
            "utils.py": """```python
def process_data(data):
    # Correction: Meilleure validation
    if not data or not isinstance(data, (list, tuple)):
        return []
    return [str(item).upper() for item in data if item is not None]

def validate_input(value):
    # Correction: Validation plus robuste
    return value is not None and len(str(value).strip()) > 0
```""",
            
            "styles.css": """```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    /* Correction: Améliorer l'accessibilité */
    line-height: 1.6;
    color: #333;
}
.container {
    max-width: 800px;
    margin: 0 auto;
    /* Correction: Responsive design */
    padding: 0 15px;
}
```"""
        }
        
        # Appliquer les "corrections" avec marqueurs markdown
        for filename, corrected_content_text in corrected_content.items():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content_text)
        
        print("❌ L'IA a réintroduit des marqueurs markdown dans les corrections")
        
        # Vérifier que les marqueurs sont présents
        for filename in corrected_content.keys():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.startswith('```') or content.endswith('```'):
                print(f"⚠️  {filename}: Contient des marqueurs markdown après correction")
        
        # ÉTAPE 3: Appliquer le nettoyage automatique
        print("\n🧹 ÉTAPE 3: Nettoyage automatique post-correction")
        
        from src.mcp.simple_validation_system import clean_markdown_artifacts
        cleaned_count = clean_markdown_artifacts(temp_dir)
        
        print(f"✅ {cleaned_count} fichiers nettoyés automatiquement")
        
        # ÉTAPE 4: Vérification finale
        print("\n🔍 ÉTAPE 4: Vérification finale")
        
        success_count = 0
        for filename in initial_files.keys():
            file_path = Path(temp_dir) / filename
            with open(file_path, 'r', encoding='utf-8') as f:
                final_content = f.read()
            
            # Vérifier que les marqueurs ont été supprimés
            if not final_content.startswith('```') and not final_content.endswith('```'):
                print(f"✅ {filename}: Nettoyé avec succès")
                
                # Vérifier que les corrections sont préservées
                if filename == "app.js" and "throw new Error" in final_content:
                    print(f"   ✓ Corrections préservées dans {filename}")
                elif filename == "utils.py" and "isinstance" in final_content:
                    print(f"   ✓ Corrections préservées dans {filename}")
                elif filename == "styles.css" and "line-height" in final_content:
                    print(f"   ✓ Corrections préservées dans {filename}")
                
                success_count += 1
            else:
                print(f"❌ {filename}: Contient encore des marqueurs markdown")
                print(f"   Début: {final_content[:50]}...")
                print(f"   Fin: ...{final_content[-50:]}")
        
        print(f"\n🎯 Résultat final: {success_count}/{len(initial_files)} fichiers correctement nettoyés")
        
        if success_count == len(initial_files):
            print("🚀 SUCCÈS COMPLET: Le cycle génération->correction->nettoyage fonctionne parfaitement!")
            print("✅ Les marqueurs markdown sont supprimés APRÈS les corrections de l'IA")
            return True
        else:
            print("❌ ÉCHEC: Le nettoyage post-correction n'a pas fonctionné correctement")
            return False

if __name__ == "__main__":
    success = test_full_correction_cycle()
    exit(0 if success else 1)
