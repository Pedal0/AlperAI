#!/usr/bin/env python3
"""
Test du système de nettoyage universel des marqueurs Markdown.
Vérifie que tous les langages sont correctement détectés et nettoyés.
"""
import tempfile
import os
from pathlib import Path
from src.mcp.simple_validation_system import clean_markdown_artifacts

def test_universal_cleanup():
    """Test le nettoyage universel sur différents langages."""
    
    # Créer un répertoire temporaire de test
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir)
        
        # Fichiers de test avec différents langages et marqueurs problématiques
        test_files = {
            'test.js': '''```javascript
console.log("Hello World");
function test() {
    return true;
}
```''',
            'test.py': '''```python
def hello():
    print("Hello World")
    return True
```''',
            'test.html': '''```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>
```''',
            'test.css': '''```css
body {
    margin: 0;
    padding: 0;
}
```''',
            'test.tsx': '''```typescript
interface Props {
    name: string;
}
const Component: React.FC<Props> = ({ name }) => {
    return <div>Hello {name}</div>;
};
```''',
            'test.php': '''```php
<?php
function hello($name) {
    return "Hello " . $name;
}
?>
```''',
            'test.go': '''```go
package main

import "fmt"

func main() {
    fmt.Println("Hello World")
}
```''',
            'test.rs': '''```rust
fn main() {
    println!("Hello World");
}
```''',
            'unknown.xyz': '''```unknown-language
This is some code in an unknown language
that should still be cleaned
```''',
            'config.yaml': '''```yaml
version: "3.8"
services:
  web:
    image: nginx
```''',
        }
        
        # Créer les fichiers avec marqueurs
        for filename, content in test_files.items():
            file_path = test_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"📁 Fichiers de test créés dans: {temp_dir}")
        print("🧹 Lancement du nettoyage universel...")
        
        # Lancer le nettoyage
        cleaned_count = clean_markdown_artifacts(temp_dir)
        
        print(f"✅ {cleaned_count} fichiers nettoyés")
        
        # Vérifier les résultats
        success_count = 0
        for filename in test_files.keys():
            file_path = test_path / filename
            with open(file_path, 'r', encoding='utf-8') as f:
                cleaned_content = f.read()
            
            # Vérifier qu'il n'y a plus de marqueurs
            if not cleaned_content.startswith('```') and not cleaned_content.endswith('```'):
                print(f"✅ {filename}: Nettoyé correctement")
                success_count += 1
            else:
                print(f"❌ {filename}: Marqueurs encore présents!")
                print(f"   Contenu: {cleaned_content[:50]}...")
        
        print(f"\n🎯 Résultat: {success_count}/{len(test_files)} fichiers correctement nettoyés")
        
        if success_count == len(test_files):
            print("🚀 SUCCÈS: Le nettoyage universel fonctionne parfaitement!")
            return True
        else:
            print("⚠️ ÉCHEC: Certains fichiers n'ont pas été nettoyés correctement")
            return False

if __name__ == "__main__":
    print("🧪 Test du système de nettoyage universel des marqueurs Markdown")
    print("=" * 60)
    test_universal_cleanup()
