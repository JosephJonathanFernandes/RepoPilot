import argparse
import sys
import os
from pathlib import Path

from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture

def main():
    parser = argparse.ArgumentParser(description="RepoPilot - Repository Analysis Tool")
    parser.add_argument("path", nargs="?", default=".", help="Path to the repository")
    parser.add_argument("--explain", action="store_true", help="Generate an LLM-powered explanation of the repository")
    
    args = parser.parse_args()
    
    target_path = Path(args.path)
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Directory '{args.path}' does not exist.", file=sys.stderr)
        return 1
        
    try:
        inventory = scan_repository(str(target_path))
    except Exception as e:
        print(f"Error scanning repository: {e}", file=sys.stderr)
        return 1
        
    facts = extract_facts(inventory)
    entrypoints = detect_entrypoints(inventory, facts)
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)
    
    # ---------------------------------------------------------
    # FORMATTING LOGIC
    # ---------------------------------------------------------
    
    print("RepoPilot")
    print("-" * 40 + "\n")
    
    # 1. PROJECT CATEGORY
    languages = sorted(facts.languages.items(), key=lambda x: x[1], reverse=True)
    primary_lang = languages[0][0] if languages else "Unknown language"
    
    patterns = sorted(architecture.patterns, key=lambda p: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(p.confidence, 0), reverse=True)
    primary_arch = patterns[0].name if patterns else "application"
    if primary_arch != "application" and "application" not in primary_arch.lower():
        primary_arch = f"{primary_arch} application"
        
    print("PROJECT")
    print(f"  {primary_lang} {primary_arch}\n")
    
    # 2. HOW TO RUN
    print("HOW TO RUN")
    run_insts = sorted(run_instructions.run, key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(r.confidence, 0), reverse=True)
    if run_insts:
        best_run = run_insts[0]
        print(f"  {best_run.command}")
        print(f"  Confidence: {best_run.confidence}")
    else:
        print("  No reliable run instruction detected.")
    print()
    
    # INSTALL
    install_insts = sorted(run_instructions.install, key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(r.confidence, 0), reverse=True)
    if install_insts:
        print("INSTALL")
        print(f"  {install_insts[0].command}\n")
        
    # 3. ENTRY POINTS
    print("ENTRY POINTS")
    valid_entrypoints = [ep for ep in entrypoints if getattr(ep, 'existence', 'OBSERVED') == 'OBSERVED']
    if not valid_entrypoints:
        print("\n  No observed entry points detected.")
    else:
        print()
        sorted_eps = sorted(valid_entrypoints, key=lambda e: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(e.confidence, 0), reverse=True)
        for ep in sorted_eps:
            print(f"  {ep.confidence:<6} {ep.path}")
            print(f"         {ep.reason}\n")
            
    # 4. ARCHITECTURE
    print("ARCHITECTURE")
    if patterns:
        for p in patterns:
            print(f"  {p.name}")
    else:
        print("  Unknown architecture")
    print()
    
    # 5. KEY COMPONENTS
    print("KEY COMPONENTS")
    if architecture.components:
        for c in architecture.components[:10]:
            print(f"  {c.path}")
    else:
        print("  No specialized components detected.")
    print()
    
    # 6. DEPENDENCIES
    print("DEPENDENCIES")
    if facts.dependencies:
        unique_deps = sorted({d.name for d in facts.dependencies})
        for dep in unique_deps:
            print(f"  {dep}")
    else:
        print("  No external dependencies detected.")
    print()
    
    # 7. EVIDENCE
    print("EVIDENCE")
    evidence_set = set()
    for ep in valid_entrypoints:
        if ep.confidence in ('HIGH', 'MEDIUM'):
            evidence_set.add(ep.path)
            
    for r in run_insts + install_insts + run_instructions.build + run_instructions.test:
        if r.confidence in ('HIGH', 'MEDIUM'):
            src = r.source
            if ' -> ' in src:
                src = src.split(' -> ')[0]
            if src.startswith('Detected Python entry point: '):
                src = src.replace('Detected Python entry point: ', '')
            elif src.startswith('go_main entry point in '):
                src = src.replace('go_main entry point in ', '')
            evidence_set.add(src)
                
    for m in facts.manifests:
        evidence_set.add(m)
        
    if architecture.components:
        for c in architecture.components[:5]:
            evidence_set.add(c.path)
            
    # Clean up any duplicates or overly verbose reasons that might have slipped in
    clean_evidence = set()
    for e in evidence_set:
        if e == 'pyproject.toml / setup.py':
            clean_evidence.add('pyproject.toml')
            clean_evidence.add('setup.py')
        else:
            clean_evidence.add(e)
            
    # Filter out anything that clearly isn't a file/folder path 
    # (though our sources are mostly paths)
            
    if clean_evidence:
        for e in sorted(clean_evidence):
            print(f"  {e}")
    else:
        print("  None")
    print()
    
    # 8. LLM EXPLANATION
    if args.explain:
        print("WHY THIS STRUCTURE?\n")
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("  LLM explanation unavailable:")
            print("  GEMINI_API_KEY is not configured.\n")
        else:
            from repopilot.evidence import create_evidence_pack
            from repopilot.llm import generate_explanation, GeminiProvider
            
            try:
                evidence_pack = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
                provider = GeminiProvider(api_key=api_key)
                explanation = generate_explanation(evidence_pack, provider)
                
                text_blocks = []
                if explanation.overview:
                    text_blocks.append(explanation.overview)
                if explanation.architecture:
                    text_blocks.append(explanation.architecture)
                if explanation.caveats:
                    text_blocks.append("Caveats:\n  - " + "\n  - ".join(explanation.caveats))
                    
                if text_blocks:
                    combined_text = "\n\n".join(text_blocks)
                    # Indent the explanation lines
                    indented_text = "\n".join("  " + line if line else "" for line in combined_text.split("\n"))
                    print(indented_text)
                else:
                    print("  No explanation generated.")
            except Exception as e:
                print("  LLM explanation unavailable:")
                indented_error = "\n".join("  " + line if line else "" for line in str(e).split("\n"))
                print(indented_error)
            print()
                
    return 0

if __name__ == "__main__":
    sys.exit(main())
