import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts

class TestFacts(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_python_repository(self):
        # Create a Python repo with requirements.txt
        (self.root / 'main.py').touch()
        (self.root / 'utils.py').touch()
        
        req = self.root / 'requirements.txt'
        req.write_text("fastapi>=0.100\npytest==7.0\n# comment\ndjango >=3.0", encoding='utf-8')
        
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        
        self.assertEqual(facts.languages['Python'], 2)
        self.assertIn('requirements.txt', facts.manifests)
        self.assertIn('pip', facts.package_managers)
        
        self.assertIn('FastAPI', facts.frameworks)
        self.assertIn('Django', facts.frameworks)
        
        deps_names = [d.name for d in facts.dependencies]
        self.assertIn('fastapi', deps_names)
        self.assertIn('django', deps_names)
        self.assertIn('pytest', deps_names)

    def test_node_repository(self):
        # Create a Node/JS repo
        (self.root / 'index.js').touch()
        (self.root / 'app.tsx').touch()
        
        pkg = self.root / 'package.json'
        pkg_data = {
            "dependencies": {
                "react": "^18.2.0",
                "express": "4.17.1"
            },
            "devDependencies": {
                "jest": "27.0.0"
            }
        }
        pkg.write_text(json.dumps(pkg_data), encoding='utf-8')
        (self.root / 'package-lock.json').touch()
        
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        
        self.assertEqual(facts.languages['JavaScript'], 1)
        self.assertEqual(facts.languages['TypeScript'], 1)
        
        self.assertIn('package.json', facts.manifests)
        self.assertIn('package-lock.json', facts.manifests)
        self.assertIn('npm', facts.package_managers)
        
        self.assertIn('React', facts.frameworks)
        self.assertIn('Express', facts.frameworks)
        
        deps = {d.name: d.version for d in facts.dependencies}
        self.assertEqual(deps['react'], '^18.2.0')
        self.assertEqual(deps['express'], '4.17.1')
        self.assertEqual(deps['jest'], '27.0.0')

    def test_mixed_repository(self):
        # Python + JS repo
        (self.root / 'backend').mkdir()
        (self.root / 'backend' / 'server.py').touch()
        
        (self.root / 'frontend').mkdir()
        (self.root / 'frontend' / 'app.jsx').touch()
        
        # Manifests at root level for now
        (self.root / 'yarn.lock').touch()
        (self.root / 'pyproject.toml').touch() # empty should not crash
        
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        
        self.assertEqual(facts.languages['Python'], 1)
        self.assertEqual(facts.languages['JavaScript'], 1)
        
        self.assertIn('yarn.lock', facts.manifests)
        self.assertIn('pyproject.toml', facts.manifests)
        self.assertIn('yarn', facts.package_managers)

    def test_go_rust_repository(self):
        (self.root / 'main.go').touch()
        (self.root / 'go.mod').touch()
        
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'main.rs').touch()
        (self.root / 'Cargo.toml').touch()
        
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        
        self.assertEqual(facts.languages['Go'], 1)
        self.assertEqual(facts.languages['Rust'], 1)
        
        self.assertIn('go.mod', facts.manifests)
        self.assertIn('Cargo.toml', facts.manifests)
        
        self.assertIn('go modules', facts.package_managers)
        self.assertIn('cargo', facts.package_managers)
        
        self.assertIn('Go modules', facts.frameworks)
        self.assertIn('Rust/Cargo', facts.frameworks)

    def test_unknown_repository(self):
        # random unknown files
        (self.root / 'script.sh').touch()
        (self.root / 'unknown.xyz').touch()
        
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        
        self.assertEqual(len(facts.languages), 0)
        self.assertEqual(len(facts.manifests), 0)
        self.assertEqual(len(facts.package_managers), 0)
        self.assertEqual(len(facts.frameworks), 0)
        self.assertEqual(len(facts.dependencies), 0)

if __name__ == '__main__':
    unittest.main()
