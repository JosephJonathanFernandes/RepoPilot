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
