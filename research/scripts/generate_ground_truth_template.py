import json
import os
from pathlib import Path

def main():
    corpus_file = Path("research/corpus.json")
    if not corpus_file.exists():
        print("corpus.json not found")
        return
        
    with open(corpus_file, "r") as f:
        corpus = json.load(f)
        
    gt_file = Path("research/ground_truth.json")
    
    if gt_file.exists():
        with open(gt_file, "r") as f:
            ground_truth = json.load(f)
    else:
        ground_truth = []
        
    existing_repos = {item["repository"] for item in ground_truth}
    
    for repo in corpus:
        name = repo["owner_name"]
        if name not in existing_repos:
            ground_truth.append({
                "repository": name,
                "entry_point": {
                    "answer": None,
                    "evidence": None
                },
                "run_command": None,
                "framework": None,
                "architecture": None
            })
            
    with open(gt_file, "w") as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Generated ground truth template for {len(ground_truth)} repos")

if __name__ == "__main__":
    main()
