import json
from pathlib import Path
try:
    import tomllib
except ImportError:
    pass

from repopilot.models import RepositoryInventory, RepositoryFacts, EntryPoint

def _is_test_or_example(path_str: str) -> bool:
    """Returns True if the path implies a test, example, or docs directory/file."""
    parts = path_str.lower().split('/')
    for p in parts:
        if p in ('test', 'tests', 'example', 'examples', 'doc', 'docs', 'tutorial', 'tutorials'):
            return True
    return False

def _inspect_python_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    eps = []
    
    if _is_test_or_example(path_str):
        # We might downgrade or ignore. The prompt says "reduce its confidence or exclude it"
        # We will exclude it to avoid false positives.
        return eps
        
    name = filepath.name
    
    # Check conventional filenames
    if name in ('main.py', 'app.py', 'run.py', 'cli.py'):
        eps.append(EntryPoint(
            path=path_str,
            type='python_script',
            confidence='MEDIUM',
            reason=f'Conventional Python entry-point filename ({name})'
        ))
        
    # Check for __main__ execution block
    try:
        content = filepath.read_text(encoding='utf-8')
        # Split strings so this file doesn't detect itself as an entry point!
        if ('if __name__ ' + '== "__main__":') in content or ('if __name__ ' + "== '__main__':") in content or ('if __name__' + '=="__main__":') in content.replace(" ", ""):
            eps.append(EntryPoint(
                path=path_str,
                type='python_module',
                confidence='HIGH',
                reason='Contains __main__ execution entry point'
            ))
    except Exception:
        pass
        
    return eps

def _inspect_go_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding='utf-8')
        if 'package main' in content and 'func main(' in content:
            return [EntryPoint(
                path=path_str,
                type='go_main',
                confidence='HIGH',
                reason='Go file with package main and func main()'
            )]
    except Exception:
        pass
    return []

def _inspect_c_cpp_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding='utf-8')
        if 'int main(' in content:
            return [EntryPoint(
                path=path_str,
                type='cpp_main',
                confidence='HIGH',
                reason='C/C++ file containing int main()'
            )]
    except Exception:
        pass
    return []

def _inspect_java_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding='utf-8')
        if 'public static void main(' in content:
            return [EntryPoint(
                path=path_str,
                type='java_main',
                confidence='HIGH',
                reason='Java file containing public static void main()'
            )]
    except Exception:
        pass
    return []

def _inspect_csharp_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding='utf-8')
        if 'static void Main(' in content or 'static int Main(' in content:
            return [EntryPoint(
                path=path_str,
                type='csharp_main',
                confidence='HIGH',
                reason='C# file containing Main()'
            )]
    except Exception:
        pass
    return []

def detect_entrypoints(inventory: RepositoryInventory, facts: RepositoryFacts) -> list[EntryPoint]:
    entrypoints = []
    root_path = Path(inventory.root)
    
    # 1. Manifest-based entry points
    if 'package.json' in facts.manifests:
        pkg_path = root_path / 'package.json'
        if pkg_path.exists():
            try:
                data = json.loads(pkg_path.read_text(encoding='utf-8'))
                
                # Helper to check and add entry point if it exists
                def _add_pkg_entry(rel_path: str, ep_type: str, reason: str):
                    if rel_path.startswith('./'):
                        rel_path = rel_path[2:]
                    if (root_path / rel_path).is_file():
                        entrypoints.append(EntryPoint(
                            path=rel_path.replace('\\', '/'),
                            type=ep_type,
                            confidence='HIGH',
                            reason=reason
                        ))
                
                if 'main' in data and isinstance(data['main'], str):
                    _add_pkg_entry(data['main'], 'package_entry', 'package.json specifies "main" entry point')
                    
                if 'bin' in data:
                    bin_data = data['bin']
                    if isinstance(bin_data, str):
                        _add_pkg_entry(bin_data, 'cli_entry', 'package.json specifies "bin" CLI entry point')
                    elif isinstance(bin_data, dict):
                        for bin_path in bin_data.values():
                            if isinstance(bin_path, str):
                                _add_pkg_entry(bin_path, 'cli_entry', 'package.json specifies "bin" CLI entry point')
            except Exception:
                pass

    if 'pyproject.toml' in facts.manifests and 'tomllib' in globals():
        pyproj_path = root_path / 'pyproject.toml'
        if pyproj_path.exists():
            try:
                data = tomllib.loads(pyproj_path.read_text(encoding='utf-8'))
                has_scripts = False
                
                # Check [project.scripts]
                if 'project' in data and 'scripts' in data['project'] and data['project']['scripts']:
                    has_scripts = True
                    
                # Check [tool.poetry.scripts]
                if 'tool' in data and 'poetry' in data['tool'] and 'scripts' in data['tool']['poetry'] and data['tool']['poetry']['scripts']:
                    has_scripts = True
                    
                if has_scripts:
                    entrypoints.append(EntryPoint(
                        path='pyproject.toml',
                        type='cli_entry',
                        confidence='HIGH',
                        reason='pyproject.toml defines console scripts'
                    ))
            except Exception:
                pass

    # 2. File-based entry points
    for file_info in inventory.files:
        path_str = file_info.path
        filepath = root_path / path_str
        ext = file_info.extension
        name = filepath.name
        
        if name == 'Dockerfile':
            try:
                content = filepath.read_text(encoding='utf-8')
                if 'ENTRYPOINT' in content or 'CMD' in content:
                    entrypoints.append(EntryPoint(
                        path=path_str,
                        type='docker_entrypoint',
                        confidence='HIGH',
                        reason='Dockerfile contains ENTRYPOINT or CMD instruction'
                    ))
            except Exception:
                pass
                
        elif ext == '.py':
            eps = _inspect_python_file(path_str, filepath)
            entrypoints.extend(eps)
            
        elif ext in ('.js', '.ts'):
            if not _is_test_or_example(path_str):
                if path_str in ('index.js', 'index.ts', 'src/index.js', 'src/index.ts'):
                    entrypoints.append(EntryPoint(
                        path=path_str,
                        type=f'{"javascript" if ext == ".js" else "typescript"}_entry',
                        confidence='MEDIUM',
                        reason='Conventional JS/TS entry-point filename'
                    ))
                    
        elif ext == '.go':
            entrypoints.extend(_inspect_go_file(path_str, filepath))
            
        elif ext in ('.c', '.cpp', '.cc', '.cxx'):
            entrypoints.extend(_inspect_c_cpp_file(path_str, filepath))
            
        elif ext == '.java':
            entrypoints.extend(_inspect_java_file(path_str, filepath))
            
        elif ext == '.cs':
            entrypoints.extend(_inspect_csharp_file(path_str, filepath))
            
    # Deduplicate
    # We prefer HIGH confidence over MEDIUM confidence for the same path and type
    final_eps = {}
    for ep in entrypoints:
        key = (ep.path, ep.type)
        existing = final_eps.get(key)
        if not existing:
            final_eps[key] = ep
        else:
            if existing.confidence != 'HIGH' and ep.confidence == 'HIGH':
                final_eps[key] = ep
                
    # Sort for deterministic output
    return sorted(list(final_eps.values()), key=lambda e: (e.confidence, e.path, e.type))
