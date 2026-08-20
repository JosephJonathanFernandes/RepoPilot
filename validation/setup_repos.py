import os
import json
import shutil
from pathlib import Path

from validation.scenarios import get_scenarios

def setup():
    base_dir = Path(__file__).parent.resolve()
    repos_dir = base_dir / "repositories"
    expected_dir = base_dir / "expected"
    results_dir = base_dir / "results"
    
    # Clean existing
    if repos_dir.exists():
        shutil.rmtree(repos_dir)
    if expected_dir.exists():
        shutil.rmtree(expected_dir)
    if results_dir.exists():
        shutil.rmtree(results_dir)
        
    repos_dir.mkdir(parents=True)
    expected_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)
    
    scenarios = get_scenarios()
    
    print(f"Setting up {len(scenarios)} validation scenarios...")
    
    for scenario in scenarios:
        repo_path = repos_dir / scenario.name
        repo_path.mkdir()
        
        # Write files
        for rel_path, content in scenario.files.items():
            file_path = repo_path / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            
        # Write expected JSON
        expected_path = expected_dir / f"{scenario.name}.json"
        expected_path.write_text(json.dumps(scenario.expected, indent=2), encoding='utf-8')
        
        print(f"  Created: {scenario.name} ({len(scenario.files)} files)")

if __name__ == '__main__':
    setup()
    print("Done.")
