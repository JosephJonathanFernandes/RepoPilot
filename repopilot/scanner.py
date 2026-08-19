import os
from pathlib import Path
from typing import List, Optional, Set

from repopilot.models import RepositoryInventory, FileInfo

DEFAULT_IGNORED_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.env'}

IMPORTANT_FILES = {
    'README.md', 'CONTRIBUTING.md', 'LICENSE', 'requirements.txt', 
    'pyproject.toml', 'package.json', 'package-lock.json', 
    'Dockerfile', 'docker-compose.yml', '.env.example', 'Makefile'
}
SOURCE_EXTENSIONS = {
    '.py', '.js', '.ts', '.go', '.rs', '.cpp', '.c', '.h', '.hpp', 
    '.java', '.rb', '.php', '.cs'
}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml', '.ini', '.xml'}

def count_lines(filepath: Path) -> Optional[int]:
    """Counts physical lines in a text file. Returns None for binary/unreadable files."""
    try:
        if filepath.is_symlink() or not filepath.is_file():
            return None
            
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return None
                
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = 0
            for _ in f:
                lines += 1
            return lines
    except (UnicodeDecodeError, OSError):
        return None

def scan_repository(root_path: str, ignored_dirs: Optional[Set[str]] = None) -> RepositoryInventory:
    """Scans a repository and returns a structured inventory."""
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_IGNORED_DIRS
        
    root = Path(root_path).resolve()
    
    all_files: List[Path] = []
    all_dirs: List[Path] = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        
        dp = Path(dirpath)
        if dp != root:
            all_dirs.append(dp)
            
        for f in filenames:
            all_files.append(dp / f)
            
    # Deterministic ordering
    all_dirs.sort()
    all_files.sort()
    
    dirs_rel = [d.relative_to(root).as_posix() for d in all_dirs]
    
    file_infos = []
    stats = {}
    important_files = []
    source_files = []
    test_files = []
    config_files = []
    
    for file_path in all_files:
        rel_path_obj = file_path.relative_to(root)
        rel_path_str = rel_path_obj.as_posix()
        
        ext = file_path.suffix.lower()
        stats[ext] = stats.get(ext, 0) + 1
        
        name = file_path.name
        is_important = name in IMPORTANT_FILES
        is_source = ext in SOURCE_EXTENSIONS
        
        is_config = ext in CONFIG_EXTENSIONS
        
        is_test = False
        name_lower = name.lower()
        if name_lower.startswith('test_') or '.test.' in name_lower or name_lower.endswith('_test.go'):
            is_test = True
        elif 'test' in rel_path_obj.parts or 'tests' in rel_path_obj.parts:
            is_test = True
            
        line_count = count_lines(file_path)
        
        file_info = FileInfo(
            path=rel_path_str,
            extension=ext,
            is_source=is_source,
            is_test=is_test,
            is_config=is_config,
            is_important=is_important,
            line_count=line_count
        )
        
        file_infos.append(file_info)
        
        if is_important: important_files.append(rel_path_str)
        if is_source: source_files.append(rel_path_str)
        if is_test: test_files.append(rel_path_str)
        if is_config: config_files.append(rel_path_str)
        
    return RepositoryInventory(
        root=str(root),
        files=file_infos,
        directories=dirs_rel,
        file_statistics=stats,
        important_files=important_files,
        source_files=source_files,
        test_files=test_files,
        config_files=config_files
    )
