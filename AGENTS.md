# AGENTS

Copychat converts project code into LLM-friendly context. This is a guide to help LLMs quickly understand and navigate the codebase. The repo is maintained by [@jlowin](https://github.com/jlowin) on GitHub[https://github.com/jlowin/copychat].

## Project Overview

Copychat is a CLI tool that prepares source code for LLM context windows by:
1. Scanning directories/files based on inclusion/exclusion patterns
2. Respecting `.gitignore` and `.ccignore` patterns
3. Formatting code with proper language tags
4. Including git diff information when requested
5. Estimating token counts for context planning

## Repository Layout

* `README.md` – overview and documentation
* `src/copychat/` – CLI and library implementation
* `tests/` – pytest suite
* `pyproject.toml` – PEP-621 metadata; build is managed by **uv**
* `.github/workflows/` – CI that lints, runs tests, and publishes to PyPI
* `.ccignore` – custom ignore patterns for copychat itself

## Core Components

* `core.py` - Main scanning functionality, git integration, and file handling
  - `scan_directory()` - Primary function for finding and processing files
  - `DiffMode` - Enum defining different git diff display modes
  - Handles `.gitignore` and `.ccignore` patterns

* `format.py` - Formats code for LLM consumption
  - `format_files()` - Formats file content with metadata
  - `estimate_tokens()` - Calculates approximate token usage

* `cli.py` - Command-line interface
  - Main entry point for user interaction
  - Parses arguments and handles output (clipboard/file)

* `sources.py` - Handles different source types (filesystem, GitHub)
  - `GitHubSource` - Fetches code from GitHub repositories

* `patterns.py` - Defines file patterns and exclusions

## Key Workflows

1. **Basic Usage**: `copychat` scans the current directory and copies formatted code to clipboard
2. **Filtered Scanning**: `copychat --include py,js` only processes specified file types
3. **Git Integration**: `copychat --diff-mode full-with-diff` shows changes with context
4. **GitHub**: `copychat --source github:user/repo` fetches remote code

## Common CLI Flags

* `--include py,js` - restrict scanned extensions
* `--exclude "**/*.test.js"` - exclude specific patterns
* `--diff-mode full-with-diff` - embed git diff chunks
* `--diff-branch main` - compare against specific branch
* `--source github:<org>/<repo>` - pull remote code via GitHub
* `--out file.md` - write to file instead of clipboard
* `--depth 2` - limit directory recursion depth

## Data Flow

1. CLI parses arguments → determines source type
2. `scan_directory()` finds matching files → applies filters
3. Git diff information is added if requested
4. `format_files()` processes content → calculates tokens
5. Formatted output is sent to clipboard/file/stdout

## Common Patterns

- Path handling uses `pathlib.Path` throughout
- File content is processed as `(path, content)` tuples
- Git operations use subprocess to call git commands
- `.ccignore` supports hierarchical pattern inheritance

## Testing

- `tests/test_integration.py` has examples of all major functionality
- `sample_project` fixture provides test files of various types

## Development

```bash
uv sync                       # install runtime + dev deps
uv run pre-commit run --all-files
uv run pytest
```

## Release Process

Pushing a semantic-version tag to `main` triggers the **Publish Copychat to PyPI** workflow, building and uploading the wheel.

## Development Guidelines

1. Fix all Ruff/Pyright warnings (`pre-commit` enforces)
2. Respect `.ccignore` and `.gitignore` patterns
3. Keep CLI flags backward-compatible
4. Document changes in `CHANGELOG.md`

## Extending the Tool

- Add new file types in `patterns.py`
- Add new source types in `sources.py`
- Add new formatting options in `format.py`
- `GitHubItem` in `sources.py` fetches issues and PRs. Pass an issue/PR URL
  (e.g. `owner/repo#123` or `https://github.com/owner/repo/issues/123`) directly
  to the main `copychat` command.

**Note to LLMs**: When working on this repository, keep this AGENTS.md file up to date with new insights that would help future LLMs quickly understand the codebase structure and functionality. This file should serve as a quick reference that reduces the need for extensive code exploration.
