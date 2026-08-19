import os
import shutil
import tempfile
import unittest
from pathlib import Path

from repopilot.scanner import scan_repository

class TestScanner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_empty_repository(self):
        inv = scan_repository(str(self.root))
        self.assertEqual(len(inv.files), 0)
        self.assertEqual(len(inv.directories), 0)
        
    def test_ignored_directories(self):
        (self.root / '.git').mkdir()
        (self.root / '.git' / 'config').touch()
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules' / 'package.json').touch()
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'main.py').touch()
        
        inv = scan_repository(str(self.root))
        
        self.assertEqual(len(inv.files), 1)
        self.assertEqual(inv.files[0].path, 'src/main.py')
        self.assertEqual(len(inv.directories), 1)
        self.assertEqual(inv.directories[0], 'src')
        
    def test_deterministic_ordering_and_relative_paths(self):
        (self.root / 'b_dir').mkdir()
        (self.root / 'a_dir').mkdir()
        (self.root / 'b_dir' / 'z.py').touch()
        (self.root / 'a_dir' / 'x.py').touch()
        (self.root / 'y.py').touch()
        
        inv = scan_repository(str(self.root))
        
        self.assertEqual(inv.directories, ['a_dir', 'b_dir'])
        self.assertEqual([f.path for f in inv.files], ['a_dir/x.py', 'b_dir/z.py', 'y.py'])
        
    def test_important_files(self):
        (self.root / 'README.md').touch()
        (self.root / 'package.json').touch()
        (self.root / 'not_important.txt').touch()
        
        inv = scan_repository(str(self.root))
        
        self.assertEqual(len(inv.important_files), 2)
        self.assertIn('README.md', inv.important_files)
        self.assertIn('package.json', inv.important_files)
        
        pkg_info = next(f for f in inv.files if f.path == 'package.json')
        self.assertTrue(pkg_info.is_important)
        
    def test_classifications(self):
        (self.root / 'main.py').touch() # source
        (self.root / 'test_main.py').touch() # test, source
        (self.root / 'config.yaml').touch() # config
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'utils.js').touch() # test, source
        
        inv = scan_repository(str(self.root))
        
        self.assertIn('main.py', inv.source_files)
        self.assertIn('test_main.py', inv.source_files)
        self.assertIn('tests/utils.js', inv.source_files)
        
        self.assertIn('test_main.py', inv.test_files)
        self.assertIn('tests/utils.js', inv.test_files)
        
        self.assertIn('config.yaml', inv.config_files)
        
    def test_line_counting(self):
        # Normal trailing newline
        p1 = self.root / 'normal.txt'
        p1.write_text("line 1\nline 2\n", encoding='utf-8')
        
        # No trailing newline
        p2 = self.root / 'no_trailing.txt'
        p2.write_text("line 1\nline 2", encoding='utf-8')
        
        # Binary file
        p3 = self.root / 'binary.bin'
        p3.write_bytes(b'\x00\x01\x02\n\x03')
        
        inv = scan_repository(str(self.root))
        
        f1 = next(f for f in inv.files if f.path == 'normal.txt')
        self.assertEqual(f1.line_count, 2)
        
        f2 = next(f for f in inv.files if f.path == 'no_trailing.txt')
        self.assertEqual(f2.line_count, 2)
        
        f3 = next(f for f in inv.files if f.path == 'binary.bin')
        self.assertIsNone(f3.line_count)

if __name__ == '__main__':
    unittest.main()
