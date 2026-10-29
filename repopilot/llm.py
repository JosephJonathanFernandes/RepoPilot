"""LLM integration — optional explanatory layer on top of deterministic evidence."""

from __future__ import annotations

import dataclasses
import json
import time
import urllib.error
import urllib.request
from typing import Protocol, Optional

from repopilot.models import ExplanationResponse, RepositoryEvidence

# The free Gemini tier is limited to 15 requests per minute; a small sleep
# between calls keeps us safely under that ceiling during benchmarks.
GEMINI_RATE_LIMIT_SLEEP = 4.0


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={self.api_key}"
        )

    def generate(self, prompt: str) -> str:
        time.sleep(GEMINI_RATE_LIMIT_SLEEP)

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }

        req = urllib.request.Request(
            self.url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        max_retries = 5
        base_delay = 2.0
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    return result["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 429 and attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise Exception(f"Failed to communicate with Gemini API: {exc}") from exc
            except urllib.error.URLError as exc:
                raise Exception(f"Failed to communicate with Gemini API: {exc}") from exc
            except (KeyError, IndexError) as exc:
                raise Exception("Unexpected response format from Gemini API") from exc

        raise Exception(f"Failed to communicate with Gemini API after {max_retries} attempts: {last_error}")


class DataclassEncoder(json.JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


def build_prompt(evidence: RepositoryEvidence) -> str:
    evidence_json = json.dumps(evidence, cls=DataclassEncoder, indent=2)

    prompt = f"""You are RepoPilot, a technical repository analysis assistant.

You have been provided with deterministic, structured evidence extracted from a codebase.
Your job is to explain the repository, connect the evidence, and communicate uncertainty.

EVIDENCE PACK:
```json
{evidence_json}
```

CRITICAL RULES:
1. Do not invent facts. If the evidence does not establish something, say: "Not determined from available repository evidence." Do not guess.
2. Distinguish evidence from interpretation. State what the evidence is, then what it implies.
3. Preserve uncertainty. Do not use definitive language if the confidence is not HIGH. Use terms like "appears to", "suggests", or "likely".
4. Do not fabricate run commands. Only explain commands contained in the RunInstructions.
5. Do not fabricate dependencies. Only mention dependencies present in RepositoryFacts.
6. Provide source traceability where practical. Mention the files or patterns that lead to your conclusions. Do NOT invent line numbers or file paths.
7. Identify important files based on evidence (e.g. they are entry points or configuration manifests).
8. Suggest potential contribution areas based purely on the structure (e.g. "Add support for additional languages", "Improve architecture detection", "Add tests for X"). Do not invent project plans. Label them as "potential areas".

FORMAT:
Respond ONLY with a valid JSON object following this exact schema:
{{
  "overview": "A concise overview of what this repository appears to be.",
  "architecture": "Explanation of the repository architecture.",
  "how_to_run": ["Step 1", "Step 2"],
  "entry_points": ["Explanation of entry point 1", "Explanation of entry point 2"],
  "important_files": ["File 1: reason", "File 2: reason"],
  "dependencies": ["Dependency 1", "Dependency 2"],
  "getting_started": "A short guide on getting started.",
  "contribution_areas": ["Potential area 1", "Potential area 2"],
  "caveats": ["Caveat 1", "Caveat 2"]
}}
"""
    return prompt


def parse_llm_response(response_text: str) -> ExplanationResponse:
    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```json", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text.rsplit("```", 1)[0]

        data = json.loads(response_text.strip())

        return ExplanationResponse(
            overview=data.get("overview", "Not determined from available repository evidence."),
            architecture=data.get("architecture", "Not determined from available repository evidence."),
            how_to_run=data.get("how_to_run", []),
            entry_points=data.get("entry_points", []),
            important_files=data.get("important_files", []),
            dependencies=data.get("dependencies", []),
            getting_started=data.get("getting_started", "Not determined from available repository evidence."),
            contribution_areas=data.get("contribution_areas", []),
            caveats=data.get("caveats", []),
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse structured LLM response: {exc}\nResponse was: {response_text}") from exc


def generate_explanation(evidence: RepositoryEvidence, provider: LLMProvider) -> ExplanationResponse:
    prompt = build_prompt(evidence)
    response_text = provider.generate(prompt)
    return parse_llm_response(response_text)
