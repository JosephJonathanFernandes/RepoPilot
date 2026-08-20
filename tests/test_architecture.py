import shutil
import tempfile
import unittest
from pathlib import Path

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture

class TestArchitecture(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def get_arch(self):
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        eps = detect_entrypoints(inventory, facts)
        insts = detect_run_instructions(inventory, facts, eps)
        return detect_architecture(inventory, facts, eps, insts)
        
    def test_flat_python_repo(self):
        (self.root / 'main.py').write_text("import utils", encoding='utf-8')
        (self.root / 'utils.py').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Flat / Script-based' for p in arch.patterns))
        self.assertEqual(len(arch.components), 0)
        self.assertTrue(any(r.source == 'main.py' and r.target == 'utils.py' for r in arch.relations))
        
    def test_python_layered_repo(self):
        for d in ['services', 'controllers', 'repositories', 'models']:
            (self.root / d).mkdir()
            (self.root / d / f'{d}.py').touch()
            
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Layered' for p in arch.patterns))
        self.assertEqual(len(arch.components), 4)
        
    def test_python_import_relationships(self):
        (self.root / 'app').mkdir()
        (self.root / 'app' / 'main.py').write_text("from app.services.user import User", encoding='utf-8')
        (self.root / 'app' / 'services').mkdir()
        (self.root / 'app' / 'services' / 'user.py').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(r.source == 'app/main.py' and r.target == 'app/services/user.py' for r in arch.relations))
        
    def test_javascript_imports(self):
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'index.js').write_text("import { User } from './user';\nrequire('lodash');", encoding='utf-8')
        (self.root / 'src' / 'user.js').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(r.source == 'src/index.js' and r.target == 'src/user.js' for r in arch.relations))
        
    def test_go_imports(self):
        (self.root / 'main.go').write_text("package main\nimport (\n\t\"fmt\"\n\t\"github.com/foo/bar\"\n)\nimport \"os\"", encoding='utf-8')
        (self.root / 'utils.go').touch()
        (self.root / 'main.go').write_text("package main\nimport \"./utils\"", encoding='utf-8')
        
        arch = self.get_arch()
        self.assertEqual(len(arch.relations), 1)
        self.assertEqual(arch.relations[0].target, 'utils.go')
        
    def test_mvc_detection(self):
        for d in ['models', 'views', 'controllers']:
            (self.root / d).mkdir()
            (self.root / d / 'foo.py').touch()
            
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'MVC-like' for p in arch.patterns))
        
    def test_frontend_detection(self):
        (self.root / 'components').mkdir()
        (self.root / 'components' / 'Button.js').touch()
        (self.root / 'package.json').write_text('{"dependencies": {"react": "18"}}', encoding='utf-8')
        
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Frontend application' for p in arch.patterns))
        
    def test_monorepo_detection(self):
        (self.root / 'packages').mkdir()
        (self.root / 'packages' / 'core').mkdir()
        (self.root / 'packages' / 'core' / 'index.js').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Monorepo' for p in arch.patterns))
        
    def test_no_architecture(self):
        (self.root / 'data.csv').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Flat / Script-based' for p in arch.patterns))
        
    def test_test_directories_not_components(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'test_app.py').touch()
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'README.md').touch()
        
        arch = self.get_arch()
        self.assertTrue(any(c.path == 'tests/' and c.category == 'tests' for c in arch.components))
        self.assertTrue(any(c.path == 'docs/' and c.category == 'documentation' for c in arch.components))
        self.assertTrue(any(p.name == 'Flat / Script-based' for p in arch.patterns), "Should be flat despite tests/docs")

    def test_monorepo_suppresses_generic_backend_frontend(self):
        (self.root / 'apps').mkdir()
        (self.root / 'apps' / 'api').mkdir()
        (self.root / 'apps' / 'api' / 'main.py').touch()
        (self.root / 'apps' / 'web').mkdir()
        (self.root / 'apps' / 'web' / 'components').mkdir()
        (self.root / 'apps' / 'web' / 'components' / 'Button.js').touch()
        (self.root / 'package.json').write_text('{"dependencies": {"react": "18"}}', encoding='utf-8')
        
        arch = self.get_arch()
        self.assertTrue(any(p.name == 'Monorepo' for p in arch.patterns))
        self.assertFalse(any(p.name == 'Backend/API application' for p in arch.patterns))
        self.assertFalse(any(p.name == 'Frontend application' for p in arch.patterns))

if __name__ == '__main__':
    unittest.main()
