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
