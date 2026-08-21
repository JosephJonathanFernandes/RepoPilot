import argparse
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from dataclasses import asdict

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture
from repopilot.evidence import create_evidence_pack
from repopilot.llm import LLMProvider

REPOSITORIES = [
    {
        "name": "black",
        "url": "https://github.com/psf/black.git",
        "category": "Python CLI"
    },
    {
        "name": "fastapi-realworld-example-app",
        "url": "https://github.com/nsidnev/fastapi-realworld-example-app.git",
        "category": "Legacy/Archived FastAPI"
    },
    {
        "name": "node-express-realworld-example-app",
        "url": "https://github.com/gothinkster/node-express-realworld-example-app.git",
        "category": "Node/Express"
    },
    {
        "name": "react-redux-realworld-example-app",
        "url": "https://github.com/gothinkster/react-redux-realworld-example-app.git",
        "category": "React/TypeScript (Archived)"
    },
    {
        "name": "golang-gin-realworld-example-app",
        "url": "https://github.com/gothinkster/golang-gin-realworld-example-app.git",
        "category": "Go"
    },
    {
        "name": "json",
        "url": "https://github.com/nlohmann/json.git",
        "category": "C/C++"
    },
    {
        "name": "spring-petclinic",
        "url": "https://github.com/spring-projects/spring-petclinic.git",
        "category": "Java"
    },
    {
        "name": "is-thirteen",
        "url": "https://github.com/jezen/is-thirteen.git",
        "category": "Poor README / Small"
    }
]

def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def run_evaluation(repo, use_llm):
    repo_dir = Path("validation/real_repos") / repo["name"]
    results_dir = Path("validation/real_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Clone and checkout
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning {repo['name']}...")
        sys.stdout.flush()
        subprocess.run(["git", "clone", repo["url"], str(repo_dir)], check=True)
    
    sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True)
    repo["sha"] = sha_proc.stdout.strip()
    
    print(f"Analyzing {repo['name']} (commit {repo['sha'][:7]})...")
    sys.stdout.flush()
    
    # 1. Deterministic Analysis
    t0 = time.time()
    
    inventory = scan_repository(str(repo_dir))
    facts = extract_facts(inventory)
    entrypoints = detect_entrypoints(inventory, facts)
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)
    
    scan_time = time.time() - t0
    
    repo_size_bytes = get_dir_size(str(repo_dir))
    file_count = len(inventory.files)
    
    # 2. LLM Analysis
    llm_time = 0
    explanation = "LLM evaluation: SKIPPED\nReason: --llm flag not provided or GEMINI_API_KEY not configured"
    llm_raw_response = None
    
    if use_llm:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            explanation = "LLM evaluation: SKIPPED\nReason: GEMINI_API_KEY not configured"
        else:
            print(f"Running LLM explanation for {repo['name']}...")
            t1 = time.time()
            evidence = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
            llm = LLMProvider(api_key=api_key)
            try:
                result = llm.explain_repository(evidence)
                llm_raw_response = asdict(result)
                explanation = f"**Summary**: {result.summary}\n\n**Architecture Explanation**:\n{result.architecture_explanation}\n\n**Run Explanation**:\n{result.run_explanation}\n\n**Uncertainties**: {result.uncertainties}"
            except Exception as e:
                explanation = f"LLM evaluation: FAILED\nReason: {e}"
            llm_time = time.time() - t1
            
    # Generate Markdown Report
    report = f"""# Repository Evaluation: {repo['name']}

**Category**: {repo['category']}
**URL**: {repo['url']}
**Commit SHA**: {repo['sha']}
**Evaluated**: {time.strftime('%Y-%m-%d')}

## Metrics
- **Repository Size**: {repo_size_bytes / 1024 / 1024:.2f} MB
- **File Count (Scanned)**: {file_count} files
- **Deterministic Scan Time**: {scan_time:.2f} seconds
- **LLM Evaluation Time**: {llm_time:.2f} seconds

---

## Part A: Deterministic Engine Output

### Facts
- **Languages**: {', '.join(facts.languages)}
- **Frameworks**: {', '.join(facts.frameworks)}
- **Manifests**: {', '.join(facts.manifests)}

### Entry Points
"""
    for ep in entrypoints:
        report += f"- `{ep.path}` ({ep.type}) - {ep.confidence} Confidence\n  - Reason: {ep.reason}\n"
    if not entrypoints:
        report += "- None detected\n"
        
    report += "\n### Run Instructions\n"
    for cat, insts in [("Install", run_instructions.install), ("Build", run_instructions.build), ("Run", run_instructions.run), ("Test", run_instructions.test)]:
        report += f"**{cat}**:\n"
        for inst in insts:
            report += f"- `{inst.command}` ({inst.confidence})\n  - Source: {inst.source}\n"
        if not insts:
            report += "- None detected\n"
            
    report += "\n### Architecture Patterns\n"
    for pat in architecture.patterns:
        report += f"- **{pat.name}** ({pat.confidence} Confidence)\n  - Evidence: {', '.join(pat.evidence)}\n"
    if not architecture.patterns:
        report += "- None detected\n"
        
    report += f"""
---

## Part B: LLM Explanation Output

{explanation}

---

## Part C: Qualitative Audit (Manual Review)

*Please fill out this section after reviewing the outputs above.*

### Component Status
| Component | Status (PASS/PARTIAL/FAIL) |
| --- | --- |
| Scanner | |
| Facts | |
| Entry points | |
| Run instructions | |
| Architecture | |
| LLM explanation | |

### Failure Notes
- **Severity** (HIGH/MEDIUM/LOW): 
- **Description**: 
- **Evidence that should have led to the correct answer**: 

"""
    
    out_file = results_dir / f"{repo['name']}_{repo['sha'][:7]}.md"
    out_file.write_text(report, encoding='utf-8')
    print(f"Saved report to {out_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--llm', action='store_true', help="Run LLM evaluation")
    args = parser.parse_args()
    
    for repo in REPOSITORIES:
        try:
            run_evaluation(repo, args.llm)
        except Exception as e:
            print(f"Failed on {repo['name']}: {e}")
