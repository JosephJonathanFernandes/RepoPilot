import ast
import re
from pathlib import Path
from collections import defaultdict
from typing import Optional

from repopilot.models import (
    RepositoryInventory, RepositoryFacts, EntryPoint, RunInstructions,
    DirectoryInfo, Component, ModuleRelation, ArchitecturePattern, Architecture
)

PURPOSE_MAP = {
    'tests': 'tests',
    'test': 'tests',
    'docs': 'documentation',
    'doc': 'documentation',
    'services': 'service',
    'service': 'service',
    'api': 'api',
    'routes': 'routing',
    'controllers': 'controller',
    'models': 'model',
    'views': 'view',
    'repositories': 'repository',
    'utils': 'utility',
    'config': 'configuration',
    'components': 'component',
    'pages': 'page',
    'middleware': 'middleware',
    'schemas': 'schema',
    'database': 'database',
    'db': 'database',
    'store': 'store',
    'hooks': 'hook',
    'packages': 'package',
    'apps': 'app'
}

def detect_architecture(inventory: RepositoryInventory, facts: RepositoryFacts, entrypoints: list[EntryPoint], run_insts: RunInstructions) -> Architecture:
    root = Path(inventory.root)
    
    # 1. Directory Structure Analysis
    directories_info = []
    dir_files = defaultdict(list)
    dir_source_files = defaultdict(list)
    
    for f in inventory.files:
        dirname = str(Path(f.path).parent).replace('\\', '/')
        if dirname == '.': 
            continue
            
        parts = dirname.split('/')
        current = ""
        for p in parts:
            current = f"{current}/{p}" if current else p
            dir_files[current].append(f)
            if f.path in inventory.source_files:
                dir_source_files[current].append(f)
                
    for dpath, files in dir_files.items():
        basename = dpath.split('/')[-1].lower()
        purpose = PURPOSE_MAP.get(basename)
        directories_info.append(DirectoryInfo(
            path=dpath + '/',
            file_count=len(files),
            source_file_count=len(dir_source_files[dpath]),
            purpose_hint=purpose if purpose else ""
        ))
    
    # 2 & 3. Module Analysis and Import Graph
    relations = []
    
    for path_str in inventory.source_files:
        filepath = root / path_str
        
        try:
            stat = filepath.stat()
            if stat.st_size > 200 * 1024:
                continue
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
            
        ext = filepath.suffix
        
        if ext == '.py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            relations.append(ModuleRelation(
                                source=path_str,
                                target=alias.name,
                                relation='imports',
                                evidence=f"import {alias.name}"
                            ))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            relations.append(ModuleRelation(
                                source=path_str,
                                target=node.module,
                                relation='imports',
                                evidence=f"from {node.module} import ..."
                            ))
            except Exception:
                pass
                
        elif ext in ('.js', '.ts', '.jsx', '.tsx'):
            import_re = re.compile(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]')
            require_re = re.compile(r'require\([\'"]([^\'"]+)[\'"]\)')
            
            for m in import_re.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(1), relation='imports', evidence=m.group(0).strip()
                ))
            for m in require_re.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(1), relation='requires', evidence=m.group(0).strip()
                ))
                
        elif ext == '.go':
            import_block = re.compile(r'import\s+\((.*?)\)', re.DOTALL)
            single_import = re.compile(r'import\s+[\'"]([^\'"]+)[\'"]')
            
            for m in import_block.finditer(content):
                block = m.group(1)
                for line in block.splitlines():
                    if '"' in line:
                        target = line.split('"')[1]
                        relations.append(ModuleRelation(
                            source=path_str, target=target, relation='imports', evidence=f'import "{target}"'
                        ))
            for m in single_import.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(1), relation='imports', evidence=m.group(0).strip()
                ))

    # Map targets
    path_map = {f.path: f.path for f in inventory.files}
    path_stem_map = {f.path.replace(f.extension, '').replace('/', '.'): f.path for f in inventory.files}
    path_stem_map_js = {f.path.replace(f.extension, ''): f.path for f in inventory.files}
    
    mapped_relations = []
    for r in relations:
        target_path = r.target
        if r.target in path_stem_map:
            target_path = path_stem_map[r.target]
        elif r.target.startswith('./') or r.target.startswith('../'):
            try:
                src_dir = root / Path(r.source).parent
                resolved = (src_dir / r.target).resolve()
                rel = resolved.relative_to(root.resolve())
                rel_str = str(rel).replace('\\', '/')
                if rel_str in path_stem_map_js:
                    target_path = path_stem_map_js[rel_str]
                elif rel_str + '.js' in path_map: target_path = rel_str + '.js'
                elif rel_str + '.ts' in path_map: target_path = rel_str + '.ts'
            except Exception:
                pass
        
        if target_path in path_map:
            mapped_relations.append(ModuleRelation(source=r.source, target=target_path, relation=r.relation, evidence=r.evidence))

    # 4. Component Identification
    components = []
    categories_found = set()
    
    for d in directories_info:
        parts = d.path.strip('/').split('/')
        # Analyze up to 2 levels deep
        if len(parts) <= 2:
            basename = parts[-1].lower()
            if basename in PURPOSE_MAP:
                purpose = PURPOSE_MAP[basename]
                components.append(Component(
                    path=d.path,
                    category=purpose,
                    confidence='MEDIUM',
                    evidence=f"Directory naming convention ('{basename}')"
                ))
                categories_found.add(basename)
                
    # 5. Architecture Pattern Detection
    patterns = []
    
    if 'packages' in categories_found or 'apps' in categories_found:
        patterns.append(ArchitecturePattern(
            name='Monorepo',
            confidence='HIGH',
            evidence=['Contains packages/ or apps/ directories']
        ))
        
    if 'models' in categories_found and 'views' in categories_found and 'controllers' in categories_found:
        patterns.append(ArchitecturePattern(
            name='MVC-like',
            confidence='HIGH',
            evidence=['Contains models/, views/, and controllers/ directories']
        ))
        
    if 'services' in categories_found and 'controllers' in categories_found and 'repositories' in categories_found:
        patterns.append(ArchitecturePattern(
            name='Layered',
            confidence='HIGH',
            evidence=['Contains services/, controllers/, and repositories/ directories']
        ))
    elif 'services' in categories_found and ('controllers' in categories_found or 'routes' in categories_found or 'api' in categories_found):
        patterns.append(ArchitecturePattern(
            name='Layered',
            confidence='MEDIUM',
            evidence=['Contains services/ and API/routing directories']
        ))
        
    is_frontend = ('components' in categories_found or 'pages' in categories_found) and ('React' in facts.frameworks or 'Vue' in facts.frameworks or 'package.json' in facts.manifests)
    if is_frontend:
        patterns.append(ArchitecturePattern(
            name='Frontend application',
            confidence='HIGH' if facts.frameworks else 'MEDIUM',
            evidence=['Contains frontend structure (components/pages)', 'Manifest/Frameworks imply frontend']
        ))
        
    if 'api' in categories_found or 'routes' in categories_found or 'controllers' in categories_found:
        if not is_frontend:
            patterns.append(ArchitecturePattern(
                name='Backend/API application',
                confidence='MEDIUM',
                evidence=['Contains routes/, controllers/, or api/ directories']
            ))
            
    if not components and len(directories_info) <= 2:
        patterns.append(ArchitecturePattern(
            name='Flat / Script-based',
            confidence='MEDIUM',
            evidence=['Minimal directory structure', 'No specialized architectural components detected']
        ))

    return Architecture(
        directories=sorted(directories_info, key=lambda x: x.path),
        components=sorted(components, key=lambda x: x.path),
        relations=mapped_relations,
        patterns=patterns
    )
