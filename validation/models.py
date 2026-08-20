from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ValidationResult:
    repository: str
    passed: bool
    findings: List[str] = field(default_factory=list)
    false_positives: List[str] = field(default_factory=list)
    false_negatives: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

@dataclass
class ConfidenceAudit:
    high_correct: int = 0
    high_incorrect: int = 0
    medium_correct: int = 0
    medium_incorrect: int = 0

@dataclass
class ValidationReport:
    repositories_evaluated: int
    scanner_results: Dict[str, Any]
    facts_results: Dict[str, Any]
    entrypoints_results: Dict[str, Any]
    run_instructions_results: Dict[str, Any]
    architecture_results: Dict[str, Any]
    false_positives: List[str]
    false_negatives: List[str]
    confidence_audit: ConfidenceAudit
    findings: List[str]
