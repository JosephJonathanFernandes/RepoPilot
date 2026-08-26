import json
import os
from pathlib import Path

# Taxonomy mapping for Architecture
ARCH_TAXONOMY = {
    "backend": "BACKEND_API", "api": "BACKEND_API", "backend/api": "BACKEND_API", "web backend": "BACKEND_API",
    "cli": "CLI_SCRIPT", "script": "CLI_SCRIPT", "cli / script": "CLI_SCRIPT",
    "library": "LIBRARY", "package": "LIBRARY",
    "frontend": "FRONTEND", "spa": "FRONTEND", "ui": "FRONTEND", "frontend application": "FRONTEND",
    "monorepo": "MONOREPO"
}

def normalize_architecture(raw):
    if not raw: return "AMBIGUOUS"
    raw_lower = raw.lower().strip()
    
    # Exact match in taxonomy
    if raw_lower in ARCH_TAXONOMY: return ARCH_TAXONOMY[raw_lower]
    
    # Heuristic mapping for combined/ambiguous terms
    if "backend" in raw_lower or "api" in raw_lower: return "BACKEND_API"
    if "cli" in raw_lower or "script" in raw_lower: return "CLI_SCRIPT"
    if "library" in raw_lower or "package" in raw_lower: return "LIBRARY"
    if "frontend" in raw_lower or "spa" in raw_lower or "ui" in raw_lower: return "FRONTEND"
    if "monorepo" in raw_lower: return "MONOREPO"
    
    return "AMBIGUOUS"

def normalize_path(path_str):
    if not path_str: return None
    path_str = str(path_str).replace("\\", "/")
    while path_str.startswith("./"):
        path_str = path_str[2:]
    return path_str.strip("/")

def normalize_command(cmd_str):
    if not cmd_str: return None
    cmd_str = str(cmd_str).strip()
    cmd_str = cmd_str.replace(" ./", " .")
    return cmd_str

def is_equivalent(actual, expected, mode="exact"):
    if expected is None: return actual is None
    if actual is None: return False
        
    actual = str(actual).lower().strip()
    expected = str(expected).lower().strip()
    
    if mode == "path":
        return normalize_path(actual) == normalize_path(expected)
        
    if mode == "command":
        actual = normalize_command(actual)
        expected = normalize_command(expected)
        if actual == expected: return True
        if actual == "make all" and expected == "make": return True
        if expected == "make all" and actual == "make": return True
        return False
        
    if mode == "framework":
        if actual == expected: return True
        if "spring" in actual and "spring" in expected: return True
        if "react" in actual and "react" in expected: return True
        if "click" in actual and "click" in expected: return True
        if "express" in actual and "express" in expected: return True
        if "starlette" in actual and "starlette" in expected: return True
        if "gin" in actual and "gin" in expected: return True
        return False

    return actual == expected

def get_answer(sys_out, field):
    if isinstance(sys_out, dict):
        if field == "primary_evidence_file":
            return sys_out.get(field)
        elif field == "entry_point":
            ep = sys_out.get("entry_points")
            if ep and isinstance(ep, list) and len(ep) > 0:
                return ep[0].get("file") or ep[0].get("path")
            return sys_out.get("entry_point")
        return sys_out.get(field)
    return None

def analyze():
    raw_file = Path("research/results/raw/results_v0.2.0.json")
    if not raw_file.exists():
        print("Raw results not found.")
        return
        
    with open(raw_file, "r") as f:
        data = json.load(f)
        
    systems = ["repopilot_d", "repopilot_d_llm", "gemini_direct"]
    
    metrics = {sys: {
        "completed": 0, "failed": 0, "latency_sum": 0.0,
        "ep_corr": 0, "cmd_corr": 0, "arch_corr": 0, "framework_corr": 0,
        "claims": {"SUPPORTED": 0, "UNSUPPORTED": 0, "CONTRADICTED": 0, "UNVERIFIABLE": 0, "ABSTAINED": 0},
        "evidence_requires": 0, "evidence_correct": 0
    } for sys in systems}
    
    for item in data:
        repo = item["repository"]
        gt = item["ground_truth"]
        
        gt_ep = gt.get("entry_point", {}).get("answer") if gt.get("entry_point") else None
        gt_evid = gt.get("entry_point", {}).get("evidence") if gt.get("entry_point") else None
        gt_cmd = gt.get("run_command")
        gt_arch = normalize_architecture(gt.get("architecture"))
        gt_fw = gt.get("framework")
        
        for sys in systems:
            sys_node = item.get(sys, {})
            sys_data = sys_node.get("results", {})
            latency = sys_node.get("latency", 0.0)
            
            if not sys_data or "error" in sys_data:
                metrics[sys]["failed"] += 1
                continue
                
            metrics[sys]["completed"] += 1
            metrics[sys]["latency_sum"] += latency
            
            actual_ep = get_answer(sys_data, "entry_point")
            actual_cmd = get_answer(sys_data, "run_command")
            actual_arch = normalize_architecture(get_answer(sys_data, "architecture"))
            actual_fw = get_answer(sys_data, "framework")
            actual_evid = get_answer(sys_data, "primary_evidence_file")
            
            ep_correct = is_equivalent(actual_ep, gt_ep, "path")
            cmd_correct = is_equivalent(actual_cmd, gt_cmd, "command")
            arch_correct = (actual_arch == gt_arch and gt_arch != "AMBIGUOUS")
            fw_correct = is_equivalent(actual_fw, gt_fw, "framework")
            evid_correct = is_equivalent(actual_evid, gt_evid, "path")
            
            if ep_correct and gt_ep: metrics[sys]["ep_corr"] += 1
            if cmd_correct and gt_cmd: metrics[sys]["cmd_corr"] += 1
            if arch_correct: metrics[sys]["arch_corr"] += 1
            if fw_correct and gt_fw: metrics[sys]["framework_corr"] += 1
            
            # Evidence calculation (EAA)
            if actual_ep and gt_evid:
                metrics[sys]["evidence_requires"] += 1
                if evid_correct: metrics[sys]["evidence_correct"] += 1
                
            # Claim-level analysis for Reliability
            def evaluate_claim(actual, expected, correct, evid_req, evid_corr):
                if actual is None:
                    return "ABSTAINED"
                if expected is None:
                    return "UNVERIFIABLE"
                if not correct:
                    return "CONTRADICTED"
                if evid_req and not evid_corr:
                    return "UNSUPPORTED"
                return "SUPPORTED"
                
            metrics[sys]["claims"][evaluate_claim(actual_ep, gt_ep, ep_correct, gt_evid is not None, evid_correct)] += 1
            metrics[sys]["claims"][evaluate_claim(actual_cmd, gt_cmd, cmd_correct, False, False)] += 1
            metrics[sys]["claims"][evaluate_claim(actual_arch, gt_arch if gt_arch != "AMBIGUOUS" else None, arch_correct, False, False)] += 1

    # Output generation
    print("### A. Completion")
    print(f"| System | Completed | Failed | Avg Latency |")
    print(f"|---|---|---|---|")
    for sys in systems:
        avg_lat = metrics[sys]['latency_sum'] / max(1, metrics[sys]['completed'])
        print(f"| {sys} | {metrics[sys]['completed']}/22 | {metrics[sys]['failed']} | {avg_lat:.2f}s |")
        
    print("\n### B. Orientation — end-to-end (Denominator 22)")
    print(f"| System | Entry | Run | Architecture | Framework |")
    print(f"|---|---|---|---|---|")
    for sys in systems:
        print(f"| {sys} | {metrics[sys]['ep_corr']}/22 | {metrics[sys]['cmd_corr']}/22 | {metrics[sys]['arch_corr']}/22 | {metrics[sys]['framework_corr']}/22 |")

    print("\n### C. Conditional accuracy (Denominator = Completed runs)")
    print(f"| System | Entry | Run | Architecture | Framework |")
    print(f"|---|---|---|---|---|")
    for sys in systems:
        c = metrics[sys]['completed']
        if c == 0: continue
        print(f"| {sys} | {metrics[sys]['ep_corr']}/{c} | {metrics[sys]['cmd_corr']}/{c} | {metrics[sys]['arch_corr']}/{c} | {metrics[sys]['framework_corr']}/{c} |")
        
    print("\n### D. Reliability (Claim Level)")
    print(f"| System | Supported | Unsupported | Contradicted | Abstained | Unverifiable |")
    print(f"|---|---|---|---|---|---|")
    for sys in systems:
        c = metrics[sys]["claims"]
        print(f"| {sys} | {c['SUPPORTED']} | {c['UNSUPPORTED']} | {c['CONTRADICTED']} | {c['ABSTAINED']} | {c['UNVERIFIABLE']} |")
        
    print("\n### E. Evidence attribution (EAA)")
    print(f"| System | EAA |")
    print(f"|---|---|")
    for sys in systems:
        req = metrics[sys]['evidence_requires']
        corr = metrics[sys]['evidence_correct']
        pct = (corr / req * 100) if req > 0 else 0
        print(f"| {sys} | {corr}/{req} ({pct:.1f}%) |")

if __name__ == "__main__":
    analyze()
