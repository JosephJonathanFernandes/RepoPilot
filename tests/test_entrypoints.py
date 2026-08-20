import json
import shutil
import tempfile
import unittest
from pathlib import Path

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints

class TestEntryPoints(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def get_eps(self):
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        return detect_entrypoints(inventory, facts)
        
    def test_python_main(self):
        (self.root / 'main.py').write_text("print('hello')", encoding='utf-8')
        (self.root / '__main__.py').write_text("if __name__ == '__main__':\n    main()", encoding='utf-8')
        eps = self.get_eps()
        
        main_ep = next((e for e in eps if e.path == 'main.py'), None)
        self.assertIsNotNone(main_ep)
        self.assertEqual(main_ep.confidence, 'MEDIUM')
        
        dunder_main = next((e for e in eps if e.path == '__main__.py'), None)
        self.assertIsNotNone(dunder_main)
        self.assertEqual(dunder_main.confidence, 'HIGH')
        
    def test_python_console_scripts(self):
        (self.root / 'pyproject.toml').write_text(
            '[project.scripts]\nmyapp = "myapp.cli:main"\n', encoding='utf-8'
        )
        eps = self.get_eps()
        pep = next((e for e in eps if e.path == 'pyproject.toml'), None)
        self.assertIsNotNone(pep)
        self.assertEqual(pep.confidence, 'HIGH')
        
    def test_javascript_package_main(self):
        (self.root / 'package.json').write_text(
            json.dumps({"main": "index.js", "bin": {"cli": "cli.js"}}), encoding='utf-8'
        )
        (self.root / 'index.js').touch()
        (self.root / 'cli.js').touch()
        
        eps = self.get_eps()
        package_eps = [e for e in eps if e.path == 'package.json']
        self.assertEqual(len(package_eps), 0)
        
        idx = next((e for e in eps if e.path == 'index.js'), None)
        self.assertIsNotNone(idx)
        self.assertEqual(idx.confidence, 'HIGH')
        
        cli = next((e for e in eps if e.path == 'cli.js'), None)
        self.assertIsNotNone(cli)
        self.assertEqual(cli.confidence, 'HIGH')
        
    def test_go_func_main(self):
        (self.root / 'main.go').write_text("package main\nfunc main() {}", encoding='utf-8')
        eps = self.get_eps()
        go_ep = next((e for e in eps if e.path == 'main.go'), None)
        self.assertIsNotNone(go_ep)
        self.assertEqual(go_ep.confidence, 'HIGH')
        
    def test_c_cpp_main(self):
        (self.root / 'main.cpp').write_text("#include <iostream>\nint main(int argc, char** argv) { return 0; }", encoding='utf-8')
        eps = self.get_eps()
        cpp_ep = next((e for e in eps if e.path == 'main.cpp'), None)
        self.assertIsNotNone(cpp_ep)
        self.assertEqual(cpp_ep.confidence, 'HIGH')
        
    def test_java_main(self):
        (self.root / 'App.java').write_text("public class App { public static void main(String[] args) {} }", encoding='utf-8')
        eps = self.get_eps()
        java_ep = next((e for e in eps if e.path == 'App.java'), None)
        self.assertIsNotNone(java_ep)
        self.assertEqual(java_ep.confidence, 'HIGH')
        
    def test_docker_entrypoint(self):
        (self.root / 'Dockerfile').write_text("FROM alpine\nENTRYPOINT [\"echo\", \"hello\"]", encoding='utf-8')
        eps = self.get_eps()
        docker_ep = next((e for e in eps if e.path == 'Dockerfile'), None)
        self.assertIsNotNone(docker_ep)
        self.assertEqual(docker_ep.confidence, 'HIGH')
        
    def test_misleading_test_directories(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'main.py').write_text("if __name__ == '__main__':\n    pass", encoding='utf-8')
        
        (self.root / 'examples').mkdir()
        (self.root / 'examples' / 'index.js').touch()
        
        eps = self.get_eps()
        self.assertEqual(len(eps), 0, "Should filter out tests and examples")
        
    def test_no_detectable_entrypoints(self):
        (self.root / 'utils.py').touch()
        (self.root / 'config.json').touch()
        eps = self.get_eps()
        self.assertEqual(len(eps), 0)

if __name__ == '__main__':
    unittest.main()
