#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

"""
Tests for README enhancement functionality
"""
import os
import unittest
from pathlib import Path
import tempfile
import shutil

# Import the modules to test
from src.preview.steps.improve_readme import improve_readme_for_preview, _check_readme_inadequacy
from src.generation.steps.check_and_enhance_readme import check_and_enhance_readme, _is_readme_detailed


class TestEnhanceReadme(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create some sample files that might be referenced in the README
        Path(self.test_dir, 'start.bat').write_text('''@echo off
rem Server startup script for Windows
set PORT=%1
if "%PORT%"=="" set PORT=8080

pip install -r requirements.txt
python app.py --port=%PORT%
''')

        Path(self.test_dir, 'start.sh').write_text('''#!/bin/bash
# Server startup script for Linux/macOS
PORT="${1:-8080}"

pip install -r requirements.txt
python app.py --port=$PORT
''')

        Path(self.test_dir, 'requirements.txt').write_text('''flask==2.0.1
requests==2.26.0
''')

        Path(self.test_dir, 'app.py').write_text('''from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)
''')

    def tearDown(self):
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_readme_inadequacy_check(self):
        """Test that the README inadequacy check correctly identifies problematic READMEs"""
        # A README that only mentions the start scripts
        inadequate_readme = '''# Sample App

## Running the Application
To run this application, simply execute the start.bat (Windows) or start.sh (Linux/macOS) script.
'''
        self.assertTrue(_check_readme_inadequacy(inadequate_readme))
        
        # A README with detailed instructions
        adequate_readme = '''# Sample App

## Installation
To install the required dependencies, run:
```bash
pip install -r requirements.txt
```

## Running the Application
To run the application, execute:
```bash
python app.py --port=8080
```

You can also use the start.bat (Windows) or start.sh (Linux/macOS) script for convenience.
'''
        self.assertFalse(_check_readme_inadequacy(adequate_readme))

    def test_is_readme_detailed(self):
        """Test that the check for detailed READMEs works correctly"""
        # A README that only mentions the start scripts
        inadequate_readme = '''# Sample App

## Running the Application
To run this application, simply execute the start.bat (Windows) or start.sh (Linux/macOS) script.
'''
        self.assertFalse(_is_readme_detailed(inadequate_readme))
        
        # A README with detailed instructions
        adequate_readme = '''# Sample App

## Installation
To install the required dependencies, run:
```bash
pip install -r requirements.txt
```

## Running the Application
To run the application, execute:
```bash
python app.py --port=8080
```

You can also use the start.bat (Windows) or start.sh (Linux/macOS) script for convenience.
'''
        self.assertTrue(_is_readme_detailed(adequate_readme))

    def test_improve_readme(self):
        """Test that the README is correctly improved with detailed instructions"""
        # Create an inadequate README
        readme_path = Path(self.test_dir, 'README.md')
        readme_path.write_text('''# Sample App

## Running the Application
To run this application, simply execute the start.bat (Windows) or start.sh (Linux/macOS) script.
''')
        
        # Improve the README
        result = improve_readme_for_preview(self.test_dir)
        self.assertTrue(result)
        
        # Check that the README now contains detailed instructions
        updated_content = readme_path.read_text()
        self.assertIn('pip install -r requirements', updated_content.lower())
        self.assertIn('python app.py', updated_content.lower())
        
    def test_improved_readme_has_separate_install_and_run_sections(self):
        """Test that the improved README has separate installation and running sections"""
        # Create an inadequate README
        readme_path = Path(self.test_dir, 'README.md')
        readme_path.write_text('''# Sample App

## Running the Application
To run this application, simply execute the start.bat (Windows) or start.sh (Linux/macOS) script.
''')
        
        # Improve the README
        improve_readme_for_preview(self.test_dir)
        
        # Check that the README now contains proper sections
        updated_content = readme_path.read_text()
        self.assertIn('## Instructions détaillées', updated_content)
        self.assertIn('### Pour Linux/macOS', updated_content)
        self.assertIn('### Pour Windows', updated_content)


if __name__ == '__main__':
    unittest.main()
