import json
import re
from pathlib import Path
try:
    import tomllib
except ImportError:
    pass

from repopilot.models import RepositoryInventory, Dependency, RepositoryFacts

def _parse_requirements_txt(filepath: Path, dependencies: list, frameworks: set):
    try:
        content = filepath.read_text(encoding='utf-8')
        for line in content.splitlines():
            line = line.split('#')[0].strip()
            if not line:
                continue
            # Basic parsing: name followed by version specifiers
            match = re.match(r'^([a-zA-Z0-9\-_]+)(.*)$', line)
            if match:
                name = match.group(1).lower()
                version = match.group(2).strip()
                dependencies.append(Dependency(name=name, version=version))
                
                if name == 'fastapi': frameworks.add('FastAPI')
                elif name == 'django': frameworks.add('Django')
                elif name == 'flask': frameworks.add('Flask')
    except Exception:
        pass

def _parse_pyproject_toml(filepath: Path, dependencies: list, frameworks: set, package_managers: set):
    if 'tomllib' not in globals():
        return
    try:
        content = filepath.read_text(encoding='utf-8')
        data = tomllib.loads(content)
        
        # Check Poetry
        if 'tool' in data and 'poetry' in data['tool']:
            package_managers.add('poetry')
            deps = data['tool']['poetry'].get('dependencies', {})
            for name, version in deps.items():
                if name.lower() != 'python':
                    v_str = str(version.get('version', '')) if isinstance(version, dict) else str(version)
                    dependencies.append(Dependency(name=name.lower(), version=v_str))
                    
                    if name.lower() == 'fastapi': frameworks.add('FastAPI')
                    elif name.lower() == 'django': frameworks.add('Django')
                    elif name.lower() == 'flask': frameworks.add('Flask')
                    
        # Check PEP 621 (project.dependencies)
        if 'project' in data and 'dependencies' in data['project']:
            # Often used with pip/setuptools/hatch/pdm
            for dep_str in data['project']['dependencies']:
                match = re.match(r'^([a-zA-Z0-9\-_]+)(.*)$', dep_str)
                if match:
                    name = match.group(1).lower()
                    version = match.group(2).strip()
                    dependencies.append(Dependency(name=name, version=version))
                    
                    if name == 'fastapi': frameworks.add('FastAPI')
                    elif name == 'django': frameworks.add('Django')
                    elif name == 'flask': frameworks.add('Flask')
    except Exception:
        pass

def _parse_package_json(filepath: Path, dependencies: list, frameworks: set):
    try:
        content = filepath.read_text(encoding='utf-8')
        data = json.loads(content)
        
        deps = data.get('dependencies', {})
        dev_deps = data.get('devDependencies', {})
        
        all_deps = {**deps, **dev_deps}
        
        for name, version in all_deps.items():
            name_lower = name.lower()
            dependencies.append(Dependency(name=name_lower, version=str(version)))
            
            if name_lower == 'react': frameworks.add('React')
            elif name_lower == 'express': frameworks.add('Express')
            elif name_lower == 'next': frameworks.add('Next.js')
            elif name_lower == 'vue': frameworks.add('Vue.js')
            elif name_lower == '@angular/core': frameworks.add('Angular')
            elif name_lower == 'svelte': frameworks.add('Svelte')
    except Exception:
        pass

def extract_facts(inventory: RepositoryInventory) -> RepositoryFacts:
    languages = {}
    manifests = []
    package_managers = set()
    frameworks = set()
    dependencies = []
    
    # 1. Languages
    lang_map = {
        '.py': 'Python',
        '.js': 'JavaScript', '.jsx': 'JavaScript',
        '.ts': 'TypeScript', '.tsx': 'TypeScript',
        '.java': 'Java',
        '.c': 'C', '.cpp': 'C++', '.h': 'C/C++', '.hpp': 'C/C++',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP'
    }
    
    for ext, count in inventory.file_statistics.items():
        if ext in lang_map:
            lang = lang_map[ext]
            languages[lang] = languages.get(lang, 0) + count
            
    # 2. Detect manifests & package managers
    root_path = Path(inventory.root)
    # Get all root level files
    root_files = {f.path for f in inventory.files if '/' not in f.path}
    
    # Python manifests
    if 'requirements.txt' in root_files:
        manifests.append('requirements.txt')
        package_managers.add('pip')
        _parse_requirements_txt(root_path / 'requirements.txt', dependencies, frameworks)
        
    if 'pyproject.toml' in root_files:
        manifests.append('pyproject.toml')
        _parse_pyproject_toml(root_path / 'pyproject.toml', dependencies, frameworks, package_managers)
        
    if 'setup.py' in root_files:
        manifests.append('setup.py')
        package_managers.add('pip')
    if 'setup.cfg' in root_files:
        manifests.append('setup.cfg')
    if 'Pipfile' in root_files:
        manifests.append('Pipfile')
        package_managers.add('pipenv')
    if 'poetry.lock' in root_files:
        manifests.append('poetry.lock')
        package_managers.add('poetry')
    if 'uv.lock' in root_files:
        manifests.append('uv.lock')
        package_managers.add('uv')
        
    # JavaScript / TypeScript manifests
    if 'package.json' in root_files:
        manifests.append('package.json')
        package_managers.add('npm') # default assumption, could be overridden by lockfiles
        _parse_package_json(root_path / 'package.json', dependencies, frameworks)
        
    if 'package-lock.json' in root_files:
        manifests.append('package-lock.json')
        package_managers.add('npm')
    if 'yarn.lock' in root_files:
        manifests.append('yarn.lock')
        package_managers.add('yarn')
    if 'pnpm-lock.yaml' in root_files:
        manifests.append('pnpm-lock.yaml')
        package_managers.add('pnpm')
    if 'bun.lockb' in root_files:
        manifests.append('bun.lockb')
        package_managers.add('bun')
        
    # Go manifests
    if 'go.mod' in root_files:
        manifests.append('go.mod')
        package_managers.add('go modules')
        frameworks.add('Go modules') # Based on prompt example: "go.mod -> Go modules"
        
    # Rust manifests
    if 'Cargo.toml' in root_files:
        manifests.append('Cargo.toml')
        package_managers.add('cargo')
        frameworks.add('Rust/Cargo') # Based on prompt example
        
    return RepositoryFacts(
        languages=languages,
        manifests=sorted(list(manifests)),
        package_managers=sorted(list(package_managers)),
        frameworks=sorted(list(frameworks)),
        dependencies=dependencies
    )
