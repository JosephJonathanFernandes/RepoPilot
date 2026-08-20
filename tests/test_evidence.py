import unittest
from pathlib import Path
from repopilot.models import (
    RepositoryInventory,
    RepositoryFacts,
    EntryPoint,
    RunInstructions,
    Architecture,
    RepositoryEvidence
)
from repopilot.evidence import create_evidence_pack

class TestEvidence(unittest.TestCase):
    def test_create_evidence_pack(self):
        inventory = RepositoryInventory(
            root="my_cool_repo",
            files=[],
            directories=[],
            file_statistics={},
            important_files=[],
            source_files=[],
            test_files=[],
            config_files=[]
        )
        facts = RepositoryFacts(languages={}, manifests=[], package_managers=[], frameworks=[], dependencies=[])
        entrypoints = []
        run_instructions = RunInstructions(install=[], build=[], run=[], test=[])
        architecture = Architecture(directories=[], components=[], relations=[], patterns=[])
        
        evidence = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
        
        self.assertIsInstance(evidence, RepositoryEvidence)
        self.assertEqual(evidence.repository_name, "my_cool_repo")
        self.assertEqual(evidence.inventory, inventory)
        self.assertEqual(evidence.facts, facts)

if __name__ == '__main__':
    unittest.main()
