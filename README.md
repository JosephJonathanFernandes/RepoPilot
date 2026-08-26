# RepoPilot

**A deterministic repository intelligence engine with evidence-backed LLM explanations.**

RepoPilot analyzes unfamiliar codebases and instantly tells you what the project is, how it’s structured, where it starts, and how to run it. It builds a provable chain of evidence directly from the repository's structure before ever consulting an LLM.

---

## Example Output

When you run RepoPilot against a repository (e.g., a Python CLI tool like `black`), you get a clean, actionable map of the codebase:

```text
RepoPilot
----------------------------------------

PROJECT
  Python Flat / Script-based application

HOW TO RUN
  black {source_file_or_directory}
  Confidence: HIGH

INSTALL
  pip install .

ENTRY POINTS

  HIGH   pyproject.toml
         pyproject.toml defines console scripts

  HIGH   src/black/__init__.py
         Contains __main__ execution entry point

ARCHITECTURE
  Flat / Script-based

KEY COMPONENTS
  .github/
  docs/
  scripts/
  src/
  tests/

DEPENDENCIES
  click
  mypy-extensions
  packaging
  pathspec
  platformdirs
  pytokens
  tomli
  typing-extensions

EVIDENCE
  .github/
  README.md
  docs/
  pyproject.toml
  scripts/
  setup.py
  src/
  tests/
```

## Why RepoPilot?

Most "AI repository tools" simply feed raw files into an LLM and hope for the best. This approach is prone to hallucination, easily confused by boilerplate, and impossible to debug.

RepoPilot takes a different approach:
1. **Deterministic First**: It uses a hand-crafted, static analysis engine to build a factual inventory of the repository.
2. **Evidence-Backed**: Every conclusion (e.g., "This is a React app") is tied to specific, observable evidence (e.g., `package.json` contains `react-scripts`).
3. **Optional LLM**: Only *after* the deterministic facts are gathered can an optional LLM be invoked to provide a high-level explanation of *why* the repository is structured the way it is. **The LLM is an explanatory layer, not the authority.**

## Quickstart

### Installation

During development, you can install RepoPilot locally:

```bash
git clone https://github.com/yourusername/RepoPilot.git
cd RepoPilot
pip install .
```

*(Once published to PyPI, you will simply use `pip install repopilot`)*

### Usage

Analyze a repository deterministically:

```bash
repopilot /path/to/repository
```

Analyze a repository and append an LLM-powered explanation (requires `GEMINI_API_KEY`):

```bash
repopilot /path/to/repository --explain
```

## How It Works

RepoPilot operates in a strict, sequential pipeline:

```text
                 ┌──────────────────┐
                 │    Repository    │
                 └────────┬─────────┘
                          ↓
                 ┌──────────────────┐
                 │     Scanner      │
                 └────────┬─────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                 ↓                 ↓
      Facts          Entry Points     Run Instructions
        └─────────────────┬─────────────────┘
                          ↓
                    Architecture
                          ↓
                    Evidence Pack
                          ↓
                ┌─────────┴─────────┐
                ↓                   ↓
        Deterministic Output    Optional LLM
                                    ↓
                              Explanation
```

### Deterministic Analysis Layers

- **Scanner**: Safely traverses the repository, ignoring common noise (e.g., `.git`, `node_modules`, `venv`) to build a clean file inventory.
- **Facts**: Extracts foundational ground truth, such as primary languages, package managers, manifests, and declared dependencies.
- **Entry Points**: Locates the true starting points of the application (e.g., `main.go`, `src/index.js`, `__main__.py`). 
- **Run Instructions**: Derives the most likely commands to install dependencies and run the application.
- **Architecture**: Classifies the repository into broad architectural patterns (e.g., `Backend/API`, `Frontend/SPA`, `Monorepo`).

### Confidence & Evidence

RepoPilot assigns a **Confidence Level** (`HIGH`, `MEDIUM`, `LOW`) to its findings. It also makes a critical distinction between observed and referenced files:
- **OBSERVED**: The file physically exists in the repository.
- **REFERENCED**: The file is explicitly declared in a configuration (like a build target in `package.json`), even if the physical artifact (like `dist/index.js`) is not committed to source control.

This prevents RepoPilot from silently ignoring valid entry points simply because a project hasn't been built yet.

## What RepoPilot does NOT do (Limitations)

To maintain safety and rigor, RepoPilot operates with strict boundaries:

- **It does not execute arbitrary repository code.**
- **It does not install repository dependencies.**
- **It does not guarantee inferred commands will run flawlessly** (it infers the *intended* commands).
- **It does not claim architecture with absolute certainty** (classifications are heuristic).
- **It does not treat LLM output as ground truth** (LLMs only provide commentary on deterministic facts).

## Development & Testing

RepoPilot features a rigorous, multi-tiered validation suite.

```bash
# 1. Run unit tests
python -m pytest tests/

# 2. Run synthetic validation
# Validates the deterministic engine against known-good mock repositories
python -m validation.runner
```

*(Note: Live evaluations against real GitHub repositories are kept in a separate, manual research workflow to prevent CI brittleness).*

## License

MIT License. See `LICENSE` for details.
