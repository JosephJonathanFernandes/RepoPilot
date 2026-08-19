import json
import re
from pathlib import Path
from typing import List

from repopilot.models import RepositoryInventory, RepositoryFacts, EntryPoint, RunInstruction, RunInstructions

INSTALL_KEYWORDS = ['install', 'setup', 'getting started']
RUN_KEYWORDS = ['run', 'usage', 'quick start', 'development']
TEST_KEYWORDS = ['test']
BUILD_KEYWORDS = ['build']

def _extract_readme_commands(filepath: Path) -> dict:
    commands = {'install': [], 'build': [], 'run': [], 'test': []}
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        current_cat = None
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check for header
            if stripped.startswith('#'):
                header_text = stripped.lstrip('#').strip().lower()
                current_cat = None
                if any(k in header_text for k in INSTALL_KEYWORDS): current_cat = 'install'
                elif any(k in header_text for k in TEST_KEYWORDS): current_cat = 'test'
                elif any(k in header_text for k in RUN_KEYWORDS): current_cat = 'run'
                elif any(k in header_text for k in BUILD_KEYWORDS): current_cat = 'build'
                continue
                
            if stripped.startswith('```'):
                if in_code_block:
                    in_code_block = False
                else:
                    if current_cat:
                        in_code_block = True
                continue
                
            if in_code_block and current_cat:
                if stripped and not stripped.startswith('#'):
                    commands[current_cat].append(stripped)
                    
    except Exception:
        pass
        
    return commands

def detect_run_instructions(inventory: RepositoryInventory, facts: RepositoryFacts, entrypoints: List[EntryPoint]) -> RunInstructions:
    root = Path(inventory.root)
    root_files = {f.path for f in inventory.files if '/' not in f.path}
    
    install, build, run, test = [], [], [], []
    
    def add(cat_list, cmd, purp, conf, src):
        cat_list.append(RunInstruction(command=cmd, purpose=purp, confidence=conf, source=src))

    # 1. README extraction
    readme_paths = [f for f in root_files if f.lower() == 'readme.md']
    if readme_paths:
        readme_path = root / readme_paths[0]
        readme_cmds = _extract_readme_commands(readme_path)
        
        for cat_list, cat_name in [(install, 'install'), (build, 'build'), (run, 'run'), (test, 'test')]:
            for cmd in readme_cmds[cat_name]:
                add(cat_list, cmd, f"Documented {cat_name} command", 'HIGH', f'{readme_paths[0]} -> {cat_name.title()}')

    # 2. Package.json scripts
    if 'package.json' in facts.manifests:
        pm = 'npm'
        if 'yarn' in facts.package_managers: pm = 'yarn'
        elif 'pnpm' in facts.package_managers: pm = 'pnpm'
        elif 'bun' in facts.package_managers: pm = 'bun'
        
        add(install, f"{pm} install", "Install Node dependencies", 'HIGH', 'package.json')
        
        pkg_path = root / 'package.json'
        try:
            data = json.loads(pkg_path.read_text(encoding='utf-8'))
            scripts = data.get('scripts', {})
            for script_name in scripts:
                cmd = f"{pm} run {script_name}"
                if pm in ('yarn', 'pnpm', 'bun') and script_name in ('start', 'test'):
                    cmd = f"{pm} {script_name}"
                elif pm == 'npm' and script_name in ('start', 'test'):
                    cmd = f"{pm} {script_name}"
                    
                cat = run
                if 'test' in script_name: cat = test
                elif 'build' in script_name: cat = build
                elif 'dev' in script_name or 'start' in script_name: cat = run
                else: continue
                
                add(cat, cmd, f"Run '{script_name}' script", 'HIGH', f'package.json scripts -> {script_name}')
        except Exception:
            pass

    # 3. Python manifests & entrypoints
    python_manifests = [m for m in facts.manifests if m in ('requirements.txt', 'pyproject.toml', 'Pipfile', 'poetry.lock', 'uv.lock', 'setup.py')]
    if python_manifests:
        if 'poetry.lock' in python_manifests:
            add(install, "poetry install", "Install dependencies via Poetry", 'HIGH', 'poetry.lock')
        elif 'Pipfile' in python_manifests:
            add(install, "pipenv install", "Install dependencies via Pipenv", 'HIGH', 'Pipfile')
        elif 'uv.lock' in python_manifests:
            add(install, "uv sync", "Install dependencies via uv", 'HIGH', 'uv.lock')
        elif 'requirements.txt' in python_manifests:
            add(install, "pip install -r requirements.txt", "Install Python dependencies", 'HIGH', 'requirements.txt')
        elif 'pyproject.toml' in python_manifests or 'setup.py' in python_manifests:
            add(install, "pip install .", "Install Python package", 'HIGH', 'pyproject.toml / setup.py')
            
    # Python entry points -> Run commands
    for ep in entrypoints:
        if ep.type in ('python_module', 'python_script'):
            # Check if it's __main__.py to run as module
            if ep.path.endswith('__main__.py'):
                module_path = ep.path.replace('__main__.py', '').replace('/', '.').strip('.')
                cmd = f"python -m {module_path}" if module_path else "python ."
            else:
                cmd = f"python {ep.path}"
                
            conf = 'MEDIUM'
            add(run, cmd, "Execute Python entry point", conf, f"Detected Python entry point: {ep.path}")

    # 4. Docker
    if 'Dockerfile' in root_files:
        add(build, "docker build -t app .", "Build Docker image", 'HIGH', 'Dockerfile')
        add(run, "docker run app", "Run Docker image", 'HIGH', 'Dockerfile')
        
    if 'docker-compose.yml' in root_files or 'compose.yml' in root_files:
        src = 'docker-compose.yml' if 'docker-compose.yml' in root_files else 'compose.yml'
        add(run, "docker compose up", "Start Docker compose services", 'HIGH', src)
        
    # 5. Makefile
    for makefile_name in ('Makefile', 'makefile'):
        if makefile_name in root_files:
            make_path = root / makefile_name
            try:
                content = make_path.read_text(encoding='utf-8')
                targets = []
                for line in content.splitlines():
                    if line.strip() and not line.startswith('\t') and not line.startswith('#') and ':' in line:
                        target = line.split(':')[0].strip()
                        if ' ' not in target and target and '=' not in target:
                            targets.append(target)
                            
                common_targets = ['all', 'install', 'build', 'run', 'dev', 'test']
                for t in targets:
                    if t in common_targets:
                        cat = run
                        if t == 'install': cat = install
                        elif t == 'build': cat = build
                        elif t == 'test': cat = test
                        elif t == 'dev': cat = run
                        elif t == 'all': cat = build
                        
                        add(cat, f"make {t}", f"Make target '{t}'", 'HIGH', f'Makefile -> {t}')
            except Exception:
                pass
            break

    # 6. Go & Rust
    if 'go.mod' in root_files:
        add(install, "go mod download", "Download Go modules", 'HIGH', 'go.mod')
        
    if 'Cargo.toml' in root_files:
        add(build, "cargo build", "Build Rust project", 'HIGH', 'Cargo.toml')
        
    # Test command fallback for Python
    if 'pytest' in [d.name for d in facts.dependencies]:
        add(test, "pytest", "Run pytest", 'MEDIUM', 'dependencies -> pytest')
    elif python_manifests and not test:
        add(test, "python -m unittest discover", "Run unittest (inferred fallback)", 'LOW', 'repository structure')

    def dedup(lst):
        seen = set()
        res = []
        for x in lst:
            if x.command not in seen:
                seen.add(x.command)
                res.append(x)
        return res
        
    return RunInstructions(
        install=dedup(install),
        build=dedup(build),
        run=dedup(run),
        test=dedup(test)
    )
