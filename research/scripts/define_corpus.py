import json
import subprocess
import os
from pathlib import Path
import shutil

REPOS = [
    # Python
    "psf/black",
    "pallets/flask",
    "tiangolo/fastapi",
    "Textualize/rich",
    # JS/TS
    "expressjs/express",
    "facebook/react",
    "nestjs/nest",
    # Go
    "gin-gonic/gin",
    "spf13/cobra",
    "gohugoio/hugo",
    # Java
    "spring-projects/spring-petclinic",
    "google/guava",
    # C/C++
    "nlohmann/json",
    "redis/redis",
    # Rust
    "rust-lang/cargo",
    "tokio-rs/tokio",
    # Monorepo / Large
    "babel/babel",
    "angular/angular",
    # Minimal / Script-based
    "chalk/chalk",
    "pypa/pip",
    # Web App Examples
    "gothinkster/node-express-realworld-example-app",
    "gothinkster/golang-gin-realworld-example-app"
]

def main():
    corpus_dir = Path("research/benchmark_corpus")
    corpus_dir.mkdir(parents=True, exist_ok=True)
    
    corpus_data = []
    
    print(f"Defining corpus of {len(REPOS)} repositories...")
    for repo in REPOS:
        repo_name = repo.split("/")[-1]
        target_dir = corpus_dir / repo_name
        
        # Clone if not exists
        if not target_dir.exists():
            print(f"Cloning {repo}...")
            subprocess.run(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(target_dir)], check=True)
            
        # Get SHA
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target_dir, capture_output=True, text=True, check=True)
        sha = result.stdout.strip()
        
        # Remove .git directory to save space and prevent git sub-module issues
        git_dir = target_dir / ".git"
        if git_dir.exists():
            # handle windows permissions
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(git_dir)])
            
        corpus_data.append({
            "owner_name": repo,
            "local_path": str(target_dir.as_posix()),
            "sha": sha
        })
        
        print(f"Pinned {repo} at {sha}")
        
    with open("research/corpus.json", "w") as f:
        json.dump(corpus_data, f, indent=2)
        
    print("Corpus defined and saved to research/corpus.json")

if __name__ == "__main__":
    main()
