import json
import dataclasses
from pathlib import Path
from validation.models import ValidationReport, ConfidenceAudit
from validation.report import generate_report

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture

def run_validation():
    base_dir = Path(__file__).parent.resolve()
    repos_dir = base_dir / "repositories"
    expected_dir = base_dir / "expected"
    results_dir = base_dir / "results"
    
    if not repos_dir.exists():
        print("Run `python -m validation.setup_repos` first.")
        return
        
    report = ValidationReport(
        repositories_evaluated=0,
        scanner_results={},
        facts_results={},
        entrypoints_results={},
        run_instructions_results={},
        architecture_results={},
        false_positives=[],
        false_negatives=[],
        confidence_audit=ConfidenceAudit(),
        findings=[]
    )
    
    for repo_path in repos_dir.iterdir():
        if not repo_path.is_dir():
            continue
            
        repo_name = repo_path.name
        expected_path = expected_dir / f"{repo_name}.json"
        
        if not expected_path.exists():
            continue
            
        with open(expected_path, 'r', encoding='utf-8') as f:
            expected = json.load(f)
            
        report.repositories_evaluated += 1
        
        # 1. Determinism test
        inv1 = scan_repository(str(repo_path))
        f1 = extract_facts(inv1)
        e1 = detect_entrypoints(inv1, f1)
        r1 = detect_run_instructions(inv1, f1, e1)
        a1 = detect_architecture(inv1, f1, e1, r1)
        
        inv2 = scan_repository(str(repo_path))
        f2 = extract_facts(inv2)
        e2 = detect_entrypoints(inv2, f2)
        r2 = detect_run_instructions(inv2, f2, e2)
        a2 = detect_architecture(inv2, f2, e2, r2)
        
        if dataclasses.asdict(a1) != dataclasses.asdict(a2):
            report.findings.append(f"[{repo_name}] NON-DETERMINISTIC architecture output detected.")
            
        # Facts evaluation
        report.facts_results[repo_name] = {}
        if "languages" in expected:
            req = set(expected["languages"].get("required", []))
            act = set(f1.languages.keys())
            fn = req - act
            if fn:
                report.false_negatives.append(f"[{repo_name}] Missed languages: {fn}")
            report.facts_results[repo_name]["Languages Recall"] = f"{len(req - fn)}/{len(req)}" if req else "N/A"
            
        if "frameworks" in expected:
            req = set(expected["frameworks"].get("required", []))
            act = set(f1.frameworks)
            fn = req - act
            if fn:
                report.false_negatives.append(f"[{repo_name}] Missed frameworks: {fn}")
            report.facts_results[repo_name]["Frameworks Recall"] = f"{len(req - fn)}/{len(req)}" if req else "N/A"
            
        # Entry points evaluation
        report.entrypoints_results[repo_name] = {}
        if "entry_points" in expected:
            req = set(expected["entry_points"].get("required", []))
            act = {e.path for e in e1}
            fn = req - act
            fp = act - req # anything not required is a false positive for entry points if the mock is exhaustive, but we said "required" schema allows extra? Let's just track it as FP if it wasn't expected.
            if fn:
                report.false_negatives.append(f"[{repo_name}] Missed entry points: {fn}")
            if fp:
                report.false_positives.append(f"[{repo_name}] False entry points: {fp}")
            
            for e in e1:
                if e.path in req:
                    if e.confidence == "HIGH": report.confidence_audit.high_correct += 1
                    else: report.confidence_audit.medium_correct += 1
                else:
                    if e.confidence == "HIGH": report.confidence_audit.high_incorrect += 1
                    else: report.confidence_audit.medium_incorrect += 1
                    
        # Architecture evaluation
        report.architecture_results[repo_name] = {}
        if "architecture_patterns" in expected:
            req = set(expected["architecture_patterns"].get("required", []))
            act = {p.name for p in a1.patterns}
            fn = req - act
            if fn:
                report.false_negatives.append(f"[{repo_name}] Missed architecture pattern: {fn}")
                
            for p in a1.patterns:
                if p.name in req:
                    if p.confidence == "HIGH": report.confidence_audit.high_correct += 1
                    else: report.confidence_audit.medium_correct += 1
                else:
                    # In this strict mock setup, we assume we defined all expected patterns
                    report.false_positives.append(f"[{repo_name}] False architecture pattern: {p.name}")
                    if p.confidence == "HIGH": report.confidence_audit.high_incorrect += 1
                    else: report.confidence_audit.medium_incorrect += 1
                    
        # Large repo specific checks
        if repo_name == "large_repo":
            if inv1.file_statistics.get(".py", 0) > 200:
                report.findings.append(f"[{repo_name}] Scanner failed to ignore node_modules properly.")
            else:
                report.findings.append(f"[{repo_name}] Scanner successfully ignored large directories.")
                
    generate_report(report, results_dir)
    print(f"Validation complete. Report saved to {results_dir / 'latest.md'}")

if __name__ == '__main__':
    run_validation()
