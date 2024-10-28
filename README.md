# copychat 📋💬

> Simple code to context

Copychat is a lightweight CLI tool that prepares your code for conversations with LLMs. It intelligently formats your source files into chat-ready context, handling everything from file selection to git diffs.

## Features

- 🎯 **Smart file selection**: Automatically identifies relevant source files while respecting `.gitignore`
- 🔍 **Git-aware**: Can include diffs and focus on changed files
- 📦 **GitHub integration**: Pull directly from repositories
- 🎨 **Clean output**: Formats code with proper language tags and metadata
- 📋 **Clipboard ready**: Results go straight to your clipboard
- 🔢 **Token smart**: Estimates token count for context planning

## Installation

```bash
pip install copychat
```

## Quick Start

Copy all Python files from current directory to clipboard:
```bash
copychat -i py
```

Copy specific files, including any git diffs:
```bash
copychat src/ tests/test_api.py --diff-mode full-with-diff
```

Use GitHub as a source instead of the local filesystem:
```bash
copychat src/ -s github:prefecthq/controlflow
```

## Usage Guide

Copychat is designed to be intuitive while offering powerful options for more complex needs. Let's walk through common use cases:

### Basic Directory Scanning

At its simplest, run `copychat` in any directory to scan and format all recognized source files:

```bash
copychat
```

This will scan the current directory, format all supported files, and copy the result to your clipboard. The output includes metadata like character and token counts to help you stay within LLM context limits.

### Targeting Specific Files

You can specify exactly what you want to include:

```bash
# Single file
copychat src/main.py

# Multiple specific files and directories
copychat src/api.py tests/test_api.py docs/

# Glob patterns
copychat src/*.py tests/**/*.md
```

### Filtering by Language

When you only want specific file types, use the `--include` flag with comma-separated extensions:

```bash
# Just Python files
copychat --include py

# Python and JavaScript
copychat --include py,js,jsx
```

### Working with Git

Copychat shines when working with git repositories. Use different diff modes to focus on what matters:

```bash
# Show only files that have changed, with their diffs
copychat --diff-mode changed-with-diff

# Show all files, but include diffs for changed ones
copychat --diff-mode full-with-diff

# Show only the git diff chunks themselves
copychat --diff-mode diff-only
```

This is particularly useful when you want to discuss code changes with an LLM.

### Excluding Files

You can exclude files that match certain patterns:

```bash
# Skip test files
copychat --exclude "**/*.test.js,**/*.spec.py"

# Skip specific directories
copychat --exclude "build/*,dist/*"
```

Copychat automatically respects your `.gitignore` file and common ignore patterns (like `node_modules`).

### GitHub Integration

Pull directly from GitHub repositories:

```bash
# Using the github: prefix
copychat --source github:username/repo

# Or just paste a GitHub URL
copychat --source https://github.com/username/repo
```

### Output Options

By default, Copychat copies to your clipboard, but you have other options:

```bash
# Append to clipboard
copychat --append

# Write to a file
copychat --out context.md

# Append to existing file
copychat --out context.md --append

# Print to screen
copychat --print

# Both copy to clipboard and save to file
copychat --out context.md
```

## Options

```bash
copychat [OPTIONS] [PATHS]...

Options:
  -s, --source TEXT     Source to scan (filesystem path, github:owner/repo, or URL)
  -o, --out PATH        Write output to file
  -a, --append          Append output instead of overwriting
  -p, --print          Print output to screen
  -i, --include TEXT    Extensions to include (comma-separated, e.g. 'py,js,ts')
  -x, --exclude TEXT    Glob patterns to exclude
  -d, --diff-mode TEXT  How to handle git diffs
  --debug              Debug mode for development
  --help               Show this message and exit
```

## Supported File Types

Copychat automatically recognizes and properly formats many common file types, including:

- Python (`.py`, `.pyi`)
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Web (`.html`, `.css`, `.scss`)
- Systems (`.c`, `.cpp`, `.rs`, `.go`)
- Config (`.yaml`, `.toml`, `.json`)
- Documentation (`.md`, `.rst`, `.txt`)
- And [many more](https://github.com/username/copychat/blob/main/copychat/patterns.py)

## Output Format

Copychat generates clean, structured output with:
- File paths and language tags
- Token count estimates
- Git diff information (when requested)
- Proper syntax highlighting markers
