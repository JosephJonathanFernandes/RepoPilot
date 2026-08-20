import argparse
import dataclasses
import json
import sys
import os
from pathlib import Path

from repopilot.scanner import scan_repository

class DataclassEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

def main():
    parser = argparse.ArgumentParser(description="Analyze a local repository")
    parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--explain", action="store_true", help="Generate an LLM-powered explanation of the repository")
    
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
    
    # Task 4: Detect Run Instructions
    from repopilot.run_instructions import detect_run_instructions
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    
    # Task 5: Detect Architecture
    from repopilot.architecture import detect_architecture
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)
        
    if args.json:
        # We can combine them into one output for json, but user just wants basic JSON, 
        # let's just dump inventory for now or we could include facts.
        output = {
            "inventory": dataclasses.asdict(inventory),
            "facts": dataclasses.asdict(facts),
            "entrypoints": [dataclasses.asdict(e) for e in entrypoints],
            "run_instructions": dataclasses.asdict(run_instructions),
            "architecture": dataclasses.asdict(architecture)
        }
        print(json.dumps(output, cls=DataclassEncoder, indent=2))
        return

    if getattr(args, 'explain', False):
        print("Deterministic repository analysis")
        print("        v")
        print("Evidence collected")
        print("        v")
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Deterministic analysis completed.\n")
            print("LLM explanation skipped:")
            print("GEMINI_API_KEY is not configured.")
            return
            
        print("Generating explanation...")
        print("        v")
        
        from repopilot.evidence import create_evidence_pack
        from repopilot.llm import generate_explanation, GeminiProvider
        
        evidence_pack = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
        provider = GeminiProvider(api_key=api_key)
        
        try:
            explanation = generate_explanation(evidence_pack, provider)
            
            print("\nRepository Overview")
            print("-" * 19)
            print(explanation.overview)
            
            print("\nArchitecture")
            print("-" * 12)
            print(explanation.architecture)
            
            print("\nHow to Run")
            print("-" * 10)
            if explanation.how_to_run:
                for idx, step in enumerate(explanation.how_to_run, 1):
                    print(f"{idx}. {step}")
            else:
                print("Not determined from available repository evidence.")
                
            print("\nEntry Points")
            print("-" * 12)
            if explanation.entry_points:
                for ep in explanation.entry_points:
                    print(f"- {ep}")
            else:
                print("Not determined from available repository evidence.")
                
            print("\nImportant Files")
            print("-" * 15)
            if explanation.important_files:
                for f in explanation.important_files:
                    print(f"- {f}")
            else:
                print("Not determined from available repository evidence.")
                
            print("\nDependencies")
            print("-" * 12)
            if explanation.dependencies:
                for d in explanation.dependencies:
                    print(f"- {d}")
            else:
                print("Not determined from available repository evidence.")
                
            print("\nGetting Started")
            print("-" * 15)
            print(explanation.getting_started)
            
            print("\nPotential Contribution Areas")
            print("-" * 28)
            if explanation.contribution_areas:
                for ca in explanation.contribution_areas:
                    print(f"- {ca}")
            else:
                print("Not determined from available repository evidence.")
                
            print("\nCaveats")
            print("-" * 7)
            if explanation.caveats:
                for c in explanation.caveats:
                    print(f"- {c}")
            else:
                print("None detected.")
                
        except Exception as e:
            print(f"\nError generating explanation: {e}")
            
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
        print("  None detected")
        
    print("\nRun Instructions")
    print("-" * 16)
    
    def print_instruction_category(title, instructions):
        if instructions:
            print(f"\n{title}:")
            for inst in instructions:
                print(f"  {inst.confidence:<6} {inst.command}")
                print(f"         Source: {inst.source}")
    
    if not (run_instructions.install or run_instructions.build or run_instructions.run or run_instructions.test):
        print("  None detected")
    else:
        print_instruction_category("INSTALL", run_instructions.install)
        print_instruction_category("BUILD", run_instructions.build)
        print_instruction_category("RUN", run_instructions.run)
        print_instruction_category("TEST", run_instructions.test)
        
    print("\nArchitecture")
    print("-" * 12)
    
    print("\nPatterns:")
    if architecture.patterns:
        for p in architecture.patterns:
            print(f"  {p.name} ({p.confidence})")
    else:
        print("  None detected")
        
    print("\nComponents:")
    if architecture.components:
        for c in architecture.components:
            print(f"  {c.path:<20} {c.category}")
    else:
        print("  None detected")
        
    print("\nRelationships:")
    ep_paths = {ep.path for ep in entrypoints}
    shown_rels = [r for r in architecture.relations if r.source in ep_paths]
    
    from collections import defaultdict
    rel_map = defaultdict(list)
    for r in shown_rels:
        rel_map[r.source].append(r.target)
        
    if rel_map:
        for src, targets in rel_map.items():
            print(f"  {src}")
            for t in sorted(set(targets))[:5]:
                print(f"      -> {t}")
            if len(set(targets)) > 5:
                print(f"      -> ... and {len(set(targets))-5} more")
            print()
    else:
        print("  None detected")
    
    print("\nFile Extensions:")
    for ext, count in sorted(inventory.file_statistics.items(), key=lambda x: x[1], reverse=True):
        ext_str = ext if ext else "<none>"
        print(f"  {ext_str}: {count}")
        
    print("\nImportant Files Found:")
    for f in inventory.important_files:
        print(f"  - {f}")

if __name__ == "__main__":
    main()
