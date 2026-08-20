import os
import argparse
from pathlib import Path
from repopilot.scanner import scan_repository
from repopilot.facts import extract_facts
from repopilot.entrypoints import detect_entrypoints
from repopilot.run_instructions import detect_run_instructions
from repopilot.architecture import detect_architecture
from repopilot.evidence import create_evidence_pack
from repopilot.llm import generate_explanation, GeminiProvider, build_prompt

def evaluate():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to repository")
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Live LLM evaluation skipped.")
        print("GEMINI_API_KEY is not configured.")
        return
        
    print(f"Running deterministic scan on {args.repo}...")
    inventory = scan_repository(args.repo)
    facts = extract_facts(inventory)
    entrypoints = detect_entrypoints(inventory, facts)
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)
    evidence = create_evidence_pack(inventory, facts, entrypoints, run_instructions, architecture)
    
    print("Sending evidence to LLM...")
    provider = GeminiProvider(api_key=api_key)
    
    try:
        response = generate_explanation(evidence, provider)
        print("\nLLM Evaluation Results:")
        print("=======================")
        print(f"Overview Present: {bool(response.overview)}")
        print(f"Architecture Present: {bool(response.architecture)}")
        print(f"Entry Points Count: {len(response.entry_points)}")
        print(f"Caveats Count: {len(response.caveats)}")
        print("\nLLM Output snippet:")
        print(response.overview[:200] + "...")
    except Exception as e:
        print(f"LLM Evaluation Failed: {e}")

if __name__ == '__main__':
    evaluate()
