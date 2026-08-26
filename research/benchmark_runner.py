import json
import time
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture
from repopilot.evidence import create_evidence_pack, format_evidence_markdown
from repopilot.llm import generate_explanation, GeminiProvider
from research.grading import (
    grade_entry_point, grade_run_command, grade_framework, match_architecture
)
from research.metrics import calculate_abstention_rate, calculate_accuracy, calculate_escr_ucr

def get_repo_tree(repo_path, max_depth=3):
    """Generates a simple tree representation of the repository."""
    # Simplified tree generation to avoid massive prompts for large repos
    cmd = ["cmd", "/c", "tree", "/F", "/A"]
    try:
        # Just use tree on Windows
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=10)
        # truncate to first 1000 lines to avoid blown context
        lines = result.stdout.split("\n")
        return "\n".join(lines[:1000])
    except Exception:
        return "Tree too large or failed"

def get_key_files(repo_path):
    """Reads contents of key files like README, package.json, etc."""
    content = ""
    key_files = ["README.md", "package.json", "pyproject.toml", "go.mod", "pom.xml", "Cargo.toml", "Makefile", "CMakeLists.txt"]
    for kf in key_files:
        p = Path(repo_path) / kf
        if p.exists() and p.is_file():
            try:
                content += f"\n--- {kf} ---\n"
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content += f.read()[:2000] # Limit to 2000 chars per file
            except Exception:
                pass
    return content

def run_gemini_direct(repo_path):
    tree = get_repo_tree(repo_path)
    files = get_key_files(repo_path)
    
    with open("research/prompts/direct_baseline.txt", "r") as f:
        prompt_template = f.read()
        
    prompt = prompt_template.replace("{repo_tree}", tree).replace("{file_contents}", files)
    
    start_time = time.time()
    try:
        provider = GeminiProvider(api_key=os.environ["GEMINI_API_KEY"])
        response_text = provider.generate(prompt)
        # Parse JSON
        import re
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            data = json.loads(response_text)
        latency = time.time() - start_time
        return data, latency
    except Exception as e:
        latency = time.time() - start_time
        return {"error": str(e)}, latency

def run_repopilot_d(repo_path):
    start_time = time.time()
    
    inventory = scan_repository(repo_path)
    facts = extract_facts(inventory)
    entrypoints = detect_entrypoints(inventory, facts)
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)
    
    pack = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
    
    latency = time.time() - start_time
    # convert dataclass to dict for serialization
    import dataclasses
    def to_dict(obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        elif isinstance(obj, list):
            return [to_dict(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: to_dict(v) for k, v in obj.items()}
        return obj
        
    return to_dict(pack), latency

def run_repopilot_d_llm(pack):
    with open("research/prompts/repopilot_explanation.txt", "r") as f:
        prompt_template = f.read()
        
    pack_md = format_evidence_markdown(pack)
    prompt = prompt_template.replace("{evidence_pack}", pack_md)
    
    start_time = time.time()
    try:
        provider = GeminiProvider(api_key=os.environ["GEMINI_API_KEY"])
        response_text = provider.generate(prompt)
        import re
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            data = json.loads(response_text)
        latency = time.time() - start_time
        return data, latency
    except Exception as e:
        latency = time.time() - start_time
        return {"error": str(e)}, latency

def format_rp_d_output(pack):
    """Extract standard benchmark fields from deterministic output."""
    ep = None
    ep_evidence = None
    if pack.get("entry_points"):
        ep = pack["entry_points"][0]["file"]
        ep_evidence = pack["entry_points"][0]["evidence"]
        
    rc = None
    if pack.get("run_instructions"):
        if pack["run_instructions"].get("run"):
            rc = pack["run_instructions"]["run"][0]["command"]
        elif pack["run_instructions"].get("build"):
            rc = pack["run_instructions"]["build"][0]["command"]
        
    arch = None
    if pack.get("architecture") and pack["architecture"].get("patterns"):
        arch = pack["architecture"]["patterns"][0]["name"]
    
    return {
        "entry_point": ep,
        "run_command": rc,
        "framework": None, # RP-D doesn't explicitly output framework as a separate top-level key yet
        "architecture": arch,
        "primary_evidence_file": ep_evidence
    }

def main():
    print("Loading corpus and ground truth...")
    with open("research/corpus.json", "r") as f:
        corpus = json.load(f)
        
    with open("research/ground_truth.json", "r") as f:
        ground_truth_list = json.load(f)
        
    ground_truth = {gt["repository"]: gt for gt in ground_truth_list}
    
    results = []
    
    for idx, repo in enumerate(corpus):
        repo_name = repo["owner_name"]
        repo_path = repo["local_path"]
        print(f"[{idx+1}/{len(corpus)}] Analyzing {repo_name}...")
        
        gt = ground_truth.get(repo_name)
        if not gt:
            print(f"Missing GT for {repo_name}, skipping.")
            continue
            
        # Run RP-D
        pack, rp_d_lat = run_repopilot_d(repo_path)
        rp_d_res = format_rp_d_output(pack)
        
        # Run RP-D+LLM
        rp_llm_res, rp_llm_lat = run_repopilot_d_llm(pack)
        
        # Run Gemini Direct
        gemini_res, gemini_lat = run_gemini_direct(repo_path)
        
        results.append({
            "repository": repo_name,
            "ground_truth": gt,
            "repopilot_d": {
                "results": rp_d_res,
                "latency": rp_d_lat
            },
            "repopilot_d_llm": {
                "results": rp_llm_res,
                "latency": rp_llm_lat + rp_d_lat
            },
            "gemini_direct": {
                "results": gemini_res,
                "latency": gemini_lat
            }
        })
        
    # Save raw results
    output_path = Path("research/results/raw/results_v0.2.0.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print("Benchmark complete. Raw results saved.")

if __name__ == "__main__":
    main()
