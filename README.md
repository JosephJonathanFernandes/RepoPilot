# RepoPilot

**A deterministic repository intelligence engine with evidence-backed LLM explanations.**

RepoPilot analyzes unfamiliar codebases and instantly tells you what the project is, how it's structured, where it starts, and how to run it. It builds a provable chain of evidence directly from the repository's structure before ever consulting an LLM.

---

## Example Output

When you run RepoPilot against a repository (e.g., a Python CLI tool like `black`), you get a clean, actionable map of the codebase:

```text
RepoPilot
----------------------------------------

PROJECT
  Python CLI_SCRIPT application

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
  CLI_SCRIPT (HIGH)

KEY COMPONENTS
  src/
  tests/
  docs/
  scripts/
  .github/

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
  pyproject.toml
  src/black/__init__.py
  README.md
  tests/
  docs/
```

## Why RepoPilot?

Most "AI repository tools" simply feed raw files into an LLM and hope for the best. This approach is prone to hallucination, easily confused by boilerplate, and impossible to debug.

RepoPilot takes a different approach:

1. **Deterministic First**: A hand-crafted static-analysis engine builds a factual inventory of the repository — no guessing, no hallucination.
2. **Evidence-Backed**: Every conclusion (e.g., "This is a React app") is tied to specific, observable evidence (e.g., `package.json` contains `react-scripts`).
3. **Optional LLM**: Only *after* the deterministic facts are gathered can an optional LLM be invoked to provide a high-level explanation of *why* the repository is structured the way it is. **The LLM is an explanatory layer, not the authority.**

## Installation

### From source (development)

```bash
git clone https://github.com/yourusername/RepoPilot.git
cd RepoPilot
pip install .
```

### From PyPI (once published)

```bash
pip install repopilot
```

### Environment setup

RepoPilot optionally uses Google's Gemini model for explanations. Set your API key:

```bash
# Option 1: environment variable
export GEMINI_API_KEY="your-key"

# Option 2: .env file (create from .env.example)
cp .env.example .env
# edit .env with your key
```

RepoPilot automatically loads `.env` via `python-dotenv`, so no extra configuration is needed.

## Usage

Analyze a repository deterministically:

```bash
repopilot /path/to/repository
```

Analyze the current directory:

```bash
repopilot
```

Append an LLM-powered explanation (requires `GEMINI_API_KEY`):

```bash
repopilot /path/to/repository --explain
```

Output as JSON (useful for scripting/integration):

```bash
repopilot /path/to/repository --json
```

Write output to a file:

```bash
repopilot /path/to/repository --output report.txt
```

Suppress informational logs:

```bash
repopilot --quiet
```

Enable debug logging:

```bash
repopilot --verbose
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

- **Scanner**: Safely traverses the repository, ignoring common noise (e.g., `.git`, `node_modules`, `.venv`) to build a clean file inventory.
- **Facts**: Extracts foundational ground truth, such as primary languages, package managers, manifests, frameworks, and declared dependencies.
- **Entry Points**: Locates the true starting points of the application (e.g., `main.go`, `src/index.js`, `__main__.py`, `package.json` `bin` fields).
- **Run Instructions**: Derives the most likely commands to install, build, run, and test the application (from README code blocks, `package.json` scripts, manifests, Makefiles, Dockerfiles).
- **Architecture**: Classifies the repository into broad architectural patterns (e.g., `BACKEND_API`, `FRONTEND`, `CLI_SCRIPT`, `LIBRARY`, `MONOREPO`).

### Confidence & Evidence

RepoPilot assigns a **Confidence Level** (`HIGH`, `MEDIUM`, `LOW`) to its findings. It also makes a critical distinction between observed and referenced files:

- **OBSERVED**: The file physically exists in the repository.
- **REFERENCED**: The file is explicitly declared in a configuration (like a build target in `package.json`), even if the physical artifact is not committed to source control.

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

### Linting & Type Checking

```bash
# Lint
ruff check repopilot tests
ruff format --check repopilot tests

# Type check
mypy repopilot
```

*(Note: Live evaluations against real GitHub repositories are kept in a separate, manual research workflow to prevent CI brittleness.)*

## Project Structure

```
repopilot/          # Core package
  cli.py            # Command-line interface (single entry point)
  scanner.py        # Repository file inventory scanner
  facts.py          # Language/manifest/dependency extraction
  entrypoints.py    # Application entry-point detection
  run_instructions.py  # Install/build/run/test command inference
  architecture.py   # Architecture pattern & component detection
  evidence.py       # Evidence pack assembly for LLM layer
  llm.py            # Optional Gemini-based explanations
  models.py         # Shared data models
  utils.py          # Shared utilities (logging, confidence sorting)
  __main__.py       # `python -m repopilot` support
tests/              # Unit tests (unittest/pytest compatible)
validation/         # Synthetic + real-repo validation scenarios
research/           # Benchmarking against ground-truth corpus
```

## License

MIT License. See `LICENSE` for details.
