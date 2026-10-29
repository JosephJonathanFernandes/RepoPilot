"""Command-line interface for RepoPilot."""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from repopilot import __version__
from repopilot.architecture import detect_architecture
from repopilot.entrypoints import detect_entrypoints
from repopilot.evidence import create_evidence_pack
from repopilot.facts import extract_facts
from repopilot.llm import GeminiProvider, generate_explanation
from repopilot.models import RepositoryInventory, RepositoryFacts
from repopilot.run_instructions import detect_run_instructions
from repopilot.scanner import scan_repository
from repopilot.utils import setup_logging

logger = logging.getLogger("repopilot")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repopilot",
        description="RepoPilot — deterministic repository intelligence engine.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )
    parser.add_argument("--version", action="version", version=f"RepoPilot {__version__}")
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Generate an LLM-powered explanation (requires GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write output to a file instead of stdout",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational log messages",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    return parser


def analyze(path: Path, explain: bool = False, as_json: bool = False) -> dict | str:
    """Run the full deterministic pipeline and return a serializable result."""
    try:
        inventory = scan_repository(str(path))
    except Exception as exc:
        logger.error("Error scanning repository: %s", exc)
        raise

    facts = extract_facts(inventory)
    entrypoints = detect_entrypoints(inventory, facts)
    run_instructions = detect_run_instructions(inventory, facts, entrypoints)
    architecture = detect_architecture(inventory, facts, entrypoints, run_instructions)

    if as_json:
        return {
            "inventory": dataclasses.asdict(inventory),
            "facts": dataclasses.asdict(facts),
            "entrypoints": [dataclasses.asdict(e) for e in entrypoints],
            "run_instructions": dataclasses.asdict(run_instructions),
            "architecture": dataclasses.asdict(architecture),
        }

    return _format_human(
        inventory, facts, entrypoints, run_instructions, architecture, explain=explain
    )


def _format_human(
    inventory: RepositoryInventory,
    facts: RepositoryFacts,
    entrypoints: list,
    run_instructions,
    architecture,
    explain: bool = False,
) -> str:
    lines: list[str] = []

    lines.append("RepoPilot")
    lines.append("-" * 40)
    lines.append("")

    # --- Project ---
    languages = sorted(facts.languages.items(), key=lambda x: x[1], reverse=True)
    primary_lang = languages[0][0] if languages else "Unknown language"

    patterns = sorted(
        architecture.patterns,
        key=lambda p: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(p.confidence, 0),
        reverse=True,
    )
    primary_arch = patterns[0].name if patterns else "application"
    if primary_arch != "application" and "application" not in primary_arch.lower():
        primary_arch = f"{primary_arch} application"

    lines.append("PROJECT")
    lines.append(f"  {primary_lang} {primary_arch}")
    lines.append("")

    # --- How to run ---
    lines.append("HOW TO RUN")
    run_insts = sorted(
        run_instructions.run,
        key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(r.confidence, 0),
        reverse=True,
    )
    if run_insts:
        best_run = run_insts[0]
        lines.append(f"  {best_run.command}")
        lines.append(f"  Confidence: {best_run.confidence}")
    else:
        lines.append("  No reliable run instruction detected.")
    lines.append("")

    # --- Install ---
    install_insts = sorted(
        run_instructions.install,
        key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(r.confidence, 0),
        reverse=True,
    )
    if install_insts:
        lines.append("INSTALL")
        lines.append(f"  {install_insts[0].command}")
        lines.append("")

    # --- Entry points ---
    lines.append("ENTRY POINTS")
    valid_entrypoints = [ep for ep in entrypoints if getattr(ep, "existence", "OBSERVED") == "OBSERVED"]
    if not valid_entrypoints:
        lines.append("  No observed entry points detected.")
    else:
        lines.append("")
        sorted_eps = sorted(
            valid_entrypoints,
            key=lambda e: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(e.confidence, 0),
            reverse=True,
        )
        for ep in sorted_eps:
            lines.append(f"  {ep.confidence:<6} {ep.path}")
            lines.append(f"         {ep.reason}")
            lines.append("")

    # --- Architecture ---
    lines.append("ARCHITECTURE")
    if patterns:
        for p in patterns:
            lines.append(f"  {p.name} ({p.confidence})")
    else:
        lines.append("  Unknown architecture")
    lines.append("")

    # --- Key components ---
    lines.append("KEY COMPONENTS")
    if architecture.components:
        for c in architecture.components[:10]:
            lines.append(f"  {c.path}")
    else:
        lines.append("  No specialized components detected.")
    lines.append("")

    # --- Dependencies ---
    lines.append("DEPENDENCIES")
    if facts.dependencies:
        unique_deps = sorted({d.name for d in facts.dependencies})
        for dep in unique_deps:
            lines.append(f"  {dep}")
    else:
        lines.append("  No external dependencies detected.")
    lines.append("")

    # --- Evidence ---
    lines.append("EVIDENCE")
    evidence_set: set[str] = set()
    for ep in valid_entrypoints:
        if ep.confidence in ("HIGH", "MEDIUM"):
            evidence_set.add(ep.path)

    all_instructions = (
        run_instructions.run
        + run_instructions.install
        + run_instructions.build
        + run_instructions.test
    )
    for r in all_instructions:
        if r.confidence in ("HIGH", "MEDIUM"):
            src = r.source
            if " -> " in src:
                src = src.split(" -> ")[0]
            if src.startswith("Detected Python entry point: "):
                src = src.replace("Detected Python entry point: ", "")
            elif src.startswith("go_main entry point in "):
                src = src.replace("go_main entry point in ", "")
            evidence_set.add(src)

    for m in facts.manifests:
        evidence_set.add(m)

    for c in architecture.components[:5]:
        evidence_set.add(c.path)

    clean_evidence = set()
    for e in evidence_set:
        if e == "pyproject.toml / setup.py":
            clean_evidence.add("pyproject.toml")
            clean_evidence.add("setup.py")
        else:
            clean_evidence.add(e)

    if clean_evidence:
        for e in sorted(clean_evidence):
            lines.append(f"  {e}")
    else:
        lines.append("  None")
    lines.append("")

    # --- LLM explanation ---
    if explain:
        lines.append("WHY THIS STRUCTURE?")
        lines.append("")

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            lines.append("  LLM explanation unavailable:")
            lines.append("  GEMINI_API_KEY is not configured.")
            lines.append("")
        else:
            try:
                evidence_pack = create_evidence_pack(
                    inventory, facts, entrypoints, run_instructions, architecture
                )
                provider = GeminiProvider(api_key=api_key)
                explanation = generate_explanation(evidence_pack, provider)

                text_blocks: list[str] = []
                if explanation.overview:
                    text_blocks.append(explanation.overview)
                if explanation.architecture:
                    text_blocks.append(explanation.architecture)
                if explanation.caveats:
                    text_blocks.append("Caveats:\n  - " + "\n  - ".join(explanation.caveats))

                if text_blocks:
                    combined_text = "\n\n".join(text_blocks)
                    indented_text = "\n".join(
                        "  " + line if line else "" for line in combined_text.split("\n")
                    )
                    lines.append(indented_text)
                else:
                    lines.append("  No explanation generated.")
            except Exception as exc:  # noqa: BLE001
                lines.append("  LLM explanation unavailable:")
                indented_error = "\n".join(
                    "  " + line if line else "" for line in str(exc).split("\n")
                )
                lines.append(indented_error)
            lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.quiet:
        setup_logging(verbose=False)
        logger.setLevel(logging.ERROR)
    elif args.verbose:
        setup_logging(verbose=True)
    else:
        setup_logging(verbose=False)

    load_dotenv()  # Load GEMINI_API_KEY from .env if present

    target_path = Path(args.path)
    if not target_path.exists() or not target_path.is_dir():
        print(f"Error: Directory '{args.path}' does not exist.", file=sys.stderr)
        return 1

    try:
        result = analyze(target_path, explain=args.explain, as_json=args.json)
    except Exception as exc:  # noqa: BLE001
        print(f"Error analyzing repository: {exc}", file=sys.stderr)
        return 1

    output_text = json.dumps(result, indent=2) if args.json else result

    if args.output:
        try:
            Path(args.output).write_text(output_text, encoding="utf-8")
            logger.info("Output written to %s", args.output)
        except OSError as exc:
            print(f"Error writing output file: {exc}", file=sys.stderr)
            return 1
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
