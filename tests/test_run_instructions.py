import json
import shutil
import tempfile
import unittest
from pathlib import Path

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions

class TestRunInstructions(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def get_instructions(self):
        inventory = scan_repository(str(self.root))
        facts = extract_facts(inventory)
        eps = detect_entrypoints(inventory, facts)
        return detect_run_instructions(inventory, facts, eps)
        
    def test_readme_extraction(self):
        readme = self.root / 'README.md'
        readme.write_text("# Installation\n```bash\npip install .\n```\n## Usage\n```\npython app.py\n```\n", encoding='utf-8')
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'pip install .' and c.confidence == 'HIGH' for c in ins.install))
        self.assertTrue(any(c.command == 'python app.py' and c.confidence == 'HIGH' for c in ins.run))

    def test_python_requirements(self):
        (self.root / 'requirements.txt').touch()
        (self.root / 'app.py').write_text("print('hi')", encoding='utf-8')
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'pip install -r requirements.txt' for c in ins.install))
        self.assertTrue(any(c.command == 'python app.py' and c.confidence == 'MEDIUM' for c in ins.run))

    def test_package_json_scripts(self):
        pkg = self.root / 'package.json'
        pkg.write_text(json.dumps({
            "scripts": {
                "dev": "vite",
                "build": "tsc",
                "test": "jest"
            }
        }), encoding='utf-8')
        (self.root / 'yarn.lock').touch() # implies yarn
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'yarn install' for c in ins.install))
        self.assertTrue(any(c.command == 'yarn run dev' for c in ins.run))
        self.assertTrue(any(c.command == 'yarn run build' for c in ins.build))
        self.assertTrue(any(c.command == 'yarn test' for c in ins.test))

    def test_npm_and_pnpm_lockfiles(self):
        # pnpm lockfile test
        pkg = self.root / 'package.json'
        pkg.write_text(json.dumps({"scripts": {"start": "node index.js"}}), encoding='utf-8')
        (self.root / 'pnpm-lock.yaml').touch()
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'pnpm install' for c in ins.install))
        self.assertTrue(any(c.command == 'pnpm start' for c in ins.run))

    def test_dockerfile_and_compose(self):
        (self.root / 'Dockerfile').touch()
        (self.root / 'docker-compose.yml').touch()
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'docker build -t app .' for c in ins.build))
        self.assertTrue(any(c.command == 'docker run app' for c in ins.run))
        self.assertTrue(any(c.command == 'docker compose up' for c in ins.run))

    def test_makefile(self):
        (self.root / 'Makefile').write_text("install:\n\techo 1\nbuild:\n\techo 2\ntest:\n\techo 3\n", encoding='utf-8')
        
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'make install' for c in ins.install))
        self.assertTrue(any(c.command == 'make build' for c in ins.build))
        self.assertTrue(any(c.command == 'make test' for c in ins.test))

    def test_test_command_fallback(self):
        # pytest inferred from dependencies
        req = self.root / 'requirements.txt'
        req.write_text("pytest==7.0.0", encoding='utf-8')
        ins = self.get_instructions()
        self.assertTrue(any(c.command == 'pytest' and c.confidence == 'MEDIUM' for c in ins.test))

    def test_no_instructions(self):
        (self.root / 'data.csv').touch()
        ins = self.get_instructions()
        self.assertEqual(len(ins.install), 0)
        self.assertEqual(len(ins.build), 0)
        self.assertEqual(len(ins.run), 0)
        self.assertEqual(len(ins.test), 0)

if __name__ == '__main__':
    unittest.main()
