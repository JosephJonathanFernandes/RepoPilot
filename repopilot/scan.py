import argparse
import dataclasses
import json
import sys
from pathlib import Path

from repopilot.scanner import scan_repository

class DataclassEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

def main():
    parser = argparse.ArgumentParser(description="RepoPilot Repository Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Path to the local repository (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of readable summary")
    
    args = parser.parse_args()
    
    target_path = Path(args.path)
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Directory '{args.path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    try:
        inventory = scan_repository(str(target_path))
    except Exception as e:
        print(f"Error scanning repository: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Task 2: Extract Facts
    from repopilot.facts import extract_facts
    facts = extract_facts(inventory)
    
    # Task 3: Detect Entry Points
    from repopilot.entrypoints import detect_entrypoints
    entrypoints = detect_entrypoints(inventory, facts)
        
    if args.json:
        # We can combine them into one output for json, but user just wants basic JSON, 
        # let's just dump inventory for now or we could include facts.
        output = {
            "inventory": dataclasses.asdict(inventory),
            "facts": dataclasses.asdict(facts),
            "entrypoints": [dataclasses.asdict(e) for e in entrypoints]
        }
        print(json.dumps(output, cls=DataclassEncoder, indent=2))
        return

    # Readable summary
    print(f"Repository Root: {inventory.root}")
    print(f"Total Files: {len(inventory.files)}")
    print(f"Total Directories: {len(inventory.directories)}")
    print(f"Source Files: {len(inventory.source_files)}")
    print(f"Test Files: {len(inventory.test_files)}")
    print(f"Config Files: {len(inventory.config_files)}")
    print(f"Important Files: {len(inventory.important_files)}")
    
    print("\nRepository Facts")
    print("-" * 16)
    
    print("\nLanguages:")
    if facts.languages:
        for lang, count in sorted(facts.languages.items(), key=lambda x: x[1], reverse=True):
            print(f"  {lang}: {count}")
    else:
        print("  None detected")
        
    print("\nManifests:")
    if facts.manifests:
        for manifest in facts.manifests:
            print(f"  {manifest}")
    else:
        print("  None detected")
        
    print("\nPackage Managers:")
    if facts.package_managers:
        for pm in facts.package_managers:
            print(f"  {pm}")
    else:
        print("  None detected")
        
    print("\nFrameworks:")
    if facts.frameworks:
        for framework in facts.frameworks:
            print(f"  {framework}")
    else:
        print("  None detected")
        
    print("\nDependencies:")
    if facts.dependencies:
        # Keep dependencies unique and sorted
        unique_deps = sorted({(d.name, d.version) for d in facts.dependencies})
        for name, version in unique_deps:
            if version:
                print(f"  {name} {version}")
            else:
                print(f"  {name}")
    else:
        print("  None detected")
        
    print("\nEntry Points")
    print("-" * 12)
    if entrypoints:
        high_eps = [e for e in entrypoints if e.confidence == 'HIGH']
        med_eps = [e for e in entrypoints if e.confidence == 'MEDIUM']
        
        if high_eps:
            print("\nHIGH:")
            for ep in high_eps:
                print(f"  {ep.path}")
                print(f"    Type: {ep.type}")
                print(f"    Reason: {ep.reason}")
                
        if med_eps:
            print("\nMEDIUM:")
            for ep in med_eps:
                print(f"  {ep.path}")
                print(f"    Type: {ep.type}")
                print(f"    Reason: {ep.reason}")
    else:
        print("\n  None detected")
    
    print("\nFile Extensions:")
    for ext, count in sorted(inventory.file_statistics.items(), key=lambda x: x[1], reverse=True):
        ext_str = ext if ext else "<none>"
        print(f"  {ext_str}: {count}")
        
    print("\nImportant Files Found:")
    for f in inventory.important_files:
        print(f"  - {f}")

if __name__ == "__main__":
    main()
