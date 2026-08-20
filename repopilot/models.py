from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class FileInfo:
    path: str
    extension: str
    is_source: bool = False
    is_test: bool = False
    is_config: bool = False
    is_important: bool = False
    line_count: Optional[int] = None

@dataclass
class RepositoryInventory:
    root: str
    files: List[FileInfo]
    directories: List[str]
    file_statistics: Dict[str, int]
    important_files: List[str]
    source_files: List[str]
    test_files: List[str]
    config_files: List[str]

@dataclass
class Dependency:
    name: str
    version: str

@dataclass
class RepositoryFacts:
    languages: Dict[str, int]
    manifests: List[str]
    package_managers: List[str]
    frameworks: List[str]
    dependencies: List[Dependency]

@dataclass
class EntryPoint:
    path: str
    type: str
    confidence: str
    reason: str

@dataclass
class RunInstruction:
    command: str
    purpose: str
    confidence: str
    source: str

@dataclass
class RunInstructions:
    install: List[RunInstruction]
    build: List[RunInstruction]
    run: List[RunInstruction]
    test: List[RunInstruction]

@dataclass
class DirectoryInfo:
    path: str
    file_count: int
    source_file_count: int
    purpose_hint: str

@dataclass
class Component:
    path: str
    category: str
    confidence: str
    evidence: str

@dataclass
class ModuleRelation:
    source: str
    target: str
    relation: str
    evidence: str

@dataclass
class ArchitecturePattern:
    name: str
    confidence: str
    evidence: List[str]

@dataclass
class Architecture:
    directories: List[DirectoryInfo]
    components: List[Component]
    relations: List[ModuleRelation]
    patterns: List[ArchitecturePattern]

@dataclass
class RepositoryEvidence:
    repository_name: str
    inventory: RepositoryInventory
    facts: RepositoryFacts
    entrypoints: List[EntryPoint]
    run_instructions: RunInstructions
    architecture: Architecture

@dataclass
class ExplanationResponse:
    overview: str
    architecture: str
    how_to_run: List[str]
    entry_points: List[str]
    important_files: List[str]
    dependencies: List[str]
    getting_started: str
    contribution_areas: List[str]
    caveats: List[str]
