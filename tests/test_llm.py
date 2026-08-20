import unittest
import json
from repopilot.models import (
    RepositoryInventory,
    RepositoryFacts,
    RunInstructions,
    Architecture,
    RepositoryEvidence,
    ExplanationResponse
)
from repopilot.llm import generate_explanation, build_prompt, parse_llm_response

class MockProvider:
    def __init__(self, response: str):
        self._response = response
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response

class TestLLM(unittest.TestCase):
    def setUp(self):
        self.evidence = RepositoryEvidence(
            repository_name="test_repo",
            inventory=RepositoryInventory(
                root="test_repo", files=[], directories=[], file_statistics={},
                important_files=[], source_files=[], test_files=[], config_files=[]
            ),
            facts=RepositoryFacts(languages={}, manifests=[], package_managers=[], frameworks=[], dependencies=[]),
            entrypoints=[],
            run_instructions=RunInstructions(install=[], build=[], run=[], test=[]),
            architecture=Architecture(directories=[], components=[], relations=[], patterns=[])
        )

    def test_build_prompt_contains_evidence(self):
        prompt = build_prompt(self.evidence)
        self.assertIn('"repository_name": "test_repo"', prompt)
        self.assertIn("CRITICAL RULES", prompt)

    def test_parse_valid_json(self):
        mock_response = """
        ```json
        {
          "overview": "Test overview",
          "architecture": "Test architecture",
          "how_to_run": ["python main.py"],
          "entry_points": ["main.py"],
          "important_files": ["main.py: entry point"],
          "dependencies": ["flask"],
          "getting_started": "Just run it.",
          "contribution_areas": ["tests"],
          "caveats": ["none"]
        }
        ```
        """
        response = parse_llm_response(mock_response)
        self.assertEqual(response.overview, "Test overview")
        self.assertEqual(response.how_to_run, ["python main.py"])

    def test_parse_missing_fields(self):
        mock_response = '{"overview": "Partial response"}'
        response = parse_llm_response(mock_response)
        self.assertEqual(response.overview, "Partial response")
        self.assertEqual(response.architecture, "Not determined from available repository evidence.")
        self.assertEqual(response.how_to_run, [])

    def test_parse_malformed_json_raises_error(self):
        with self.assertRaises(ValueError):
            parse_llm_response("Not JSON at all")

    def test_generate_explanation(self):
        mock_response = '{"overview": "Great repo"}'
        provider = MockProvider(mock_response)
        response = generate_explanation(self.evidence, provider)
        
        self.assertIn("CRITICAL RULES", provider.last_prompt)
        self.assertEqual(response.overview, "Great repo")

if __name__ == '__main__':
    unittest.main()
