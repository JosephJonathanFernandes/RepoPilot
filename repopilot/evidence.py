from pathlib import Path

from repopilot.models import (
    RepositoryInventory,
    RepositoryFacts,
    EntryPoint,
    RunInstructions,
    Architecture,
    RepositoryEvidence
)

def create_evidence_pack(
    inventory: RepositoryInventory,
    facts: RepositoryFacts,
    entrypoints: list[EntryPoint],
    run_instructions: RunInstructions,
    architecture: Architecture
) -> RepositoryEvidence:
    repo_name = Path(inventory.root).name
    return RepositoryEvidence(
        repository_name=repo_name,
        inventory=inventory,
        facts=facts,
        entrypoints=entrypoints,
        run_instructions=run_instructions,
        architecture=architecture
    )

def format_evidence_markdown(pack: dict) -> str:
    """Formats the Evidence Pack dictionary into a token-efficient Markdown string for LLMs."""
    md = []
    
    # 1. Facts
    facts = pack.get("facts", {})
    md.append("## Manifests Found")
    md.append(", ".join(facts.get("manifests", [])) or "None")
    
    md.append("\n## Frameworks & Dependencies")
    md.append(", ".join(facts.get("frameworks", [])) or "None")
    
    # deps is a list of dicts e.g., [{'name': 'click', 'manager': 'pip', 'version': '*'}]
    deps = [d.get("name") for d in facts.get("dependencies", []) if d.get("name")]
    if len(deps) > 50:
        md.append(f"\n*Dependencies (truncated {len(deps)} total):*")
        md.append(", ".join(deps[:50]) + " ...")
    else:
        md.append(f"\n*Dependencies:* {', '.join(deps) or 'None'}")
        
    # 2. Entry Points
    md.append("\n## Entry Points Detected by Deterministic Layer")
    eps = pack.get("entrypoints", [])
    if not eps:
        md.append("None")
    else:
        for ep in eps:
            md.append(f"- **{ep.get('path')}** (Type: {ep.get('type')}, Confidence: {ep.get('confidence')})")
            md.append(f"  Reason: {ep.get('reason')}")
            
    # 3. Run Instructions
    md.append("\n## Run Instructions Detected by Deterministic Layer")
    ri = pack.get("run_instructions", {})
    
    md.append("### Run Commands")
    if not ri.get("run"):
        md.append("None")
    for r in ri.get("run", []):
        md.append(f"- `{r.get('command')}` (Source: {r.get('source_file')})")
        
    md.append("### Build Commands")
    if not ri.get("build"):
        md.append("None")
    for b in ri.get("build", []):
        md.append(f"- `{b.get('command')}` (Source: {b.get('source_file')})")
        
    # 4. Architecture
    md.append("\n## Architecture Detected by Deterministic Layer")
    arch = pack.get("architecture", {})
    patterns = arch.get("patterns", [])
    if not patterns:
        md.append("None (AMBIGUOUS)")
    else:
        for p in patterns:
            md.append(f"- **{p.get('name')}** (Confidence: {p.get('confidence')})")
            md.append(f"  Evidence: {', '.join(p.get('evidence', []))}")
            
    # 5. Inventory Summary
    # Rather than dumping thousands of file paths, summarize.
    md.append("\n## Inventory Summary")
    inv = pack.get("inventory", {})
    source_files = inv.get("source_files", [])
    if len(source_files) > 100:
        md.append(f"- Total source files: {len(source_files)}")
        md.append("- Top directories containing source code:")
        
        # Simple directory frequency counting
        dirs = {}
        for f in source_files:
            if "/" in f:
                d = "/".join(f.split("/")[:-1])
                dirs[d] = dirs.get(d, 0) + 1
            else:
                dirs["root"] = dirs.get("root", 0) + 1
                
        sorted_dirs = sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:10]
        for d, count in sorted_dirs:
            md.append(f"  - `{d}` ({count} files)")
    else:
        md.append("- Source files:\n  - " + "\n  - ".join(source_files))
        
    return "\n".join(md)
