# Copychat 📋🐈‍⬛

**Simple code-to-context.**

Copychat is a lightweight CLI tool that prepares your code for conversations with LLMs. It intelligently formats your source files into chat-ready context, handling everything from file selection to git diffs.

## Features

- 🎯 **Smart file selection**: Automatically identifies relevant source files while respecting `.gitignore`
- 🔍 **Git-aware**: Can include diffs and focus on changed files
- 📦 **GitHub integration**: Pull directly from repositories
- 🎨 **Clean output**: Formats code with proper language tags and metadata
- 📋 **Clipboard ready**: Results go straight to your clipboard
- 🔢 **Token smart**: Estimates token count for context planning

## Running Copychat

You can use [uv](https://docs.astral.sh/uv/) to run copychat directly from the command line, without needing to install it first:
```bash
uvx copychat
```

Frequent users may want to add the following alias to their `.zshrc` or `.bashrc`:
```bash
alias cc="uvx copychat"
```

This permits you to quickly copy context by running e.g. `cc docs/getting-started/ src/core/` from any directory, in any environment.

If you want to save a few milliseconds, you can install copychat globally with `uv tool install copychat` or add it to your environment with `uv add copychat`. And of course, `pip install copychat` works too.

## Quick Start
Collect, format, and copy all source code in the current directory (and subdirectories) to the clipboard:
```bash
copychat
```

Copy only Python files to clipboard:
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

# See what changed since branching from develop
copychat --diff-mode diff-only --diff-branch develop
```

The `-diff-mode` and `--diff-branch` options are particularly useful when you want to:
- Review any changes you've made, either in isolation or in context
- Compare changes against a specific branch

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

#### Reading GitHub Repositories

Pull directly from GitHub repositories:

```bash
# Using the github: prefix
copychat --source github:username/repo

# Or just paste a GitHub URL
copychat --source https://github.com/username/repo

# Process specific paths within the repository
copychat --source github:username/repo src/main.py tests/
```

The `--source` flag specifies where to look (GitHub, filesystem, etc.), and then any additional arguments specify which paths within that source to process. This means you can target specific files or directories within a GitHub repository just like you would with local files.

#### Reading GitHub Issues, PRs & Discussions

Copy the full text and comment history of a GitHub issue, pull request, or discussion by
passing the identifier directly to the main command:

```bash
# Issues and PRs
copychat owner/repo#123
copychat https://github.com/owner/repo/issues/123
copychat https://github.com/owner/repo/pull/456

# Discussions  
copychat https://github.com/owner/repo/discussions/789
```

For pull requests, the diff is included by default, giving you complete context of the proposed changes.

Set `GITHUB_TOKEN` or use `--token` if you need to access private content or want higher rate limits.

#### Reading Individual GitHub Files

You can fetch individual files directly from GitHub without cloning the entire repository by using blob URLs:

```bash
# Fetch a specific file from a commit/branch/tag
copychat https://github.com/owner/repo/blob/main/src/api.py
copychat https://github.com/owner/repo/blob/v1.2.3/config/settings.yaml
copychat https://github.com/owner/repo/blob/abc123def/docs/README.md
```

This is perfect for quickly grabbing specific files for context without the overhead of repository cloning.

The output is formatted like other files, with XML-style tags and proper language detection.

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

### Verbose Output

Use the `--verbose` flag (or `-v`) to include detailed file information in the output, including token counts:

```bash
copychat -v
```

### Limiting Directory Depth

Control how deep copychat scans subdirectories:

```bash
# Only files in current directory
copychat --depth 0

# Current directory and immediate subdirectories only
copychat --depth 1

# Scan up to 3 levels deep
copychat --depth 3
```

## Options

```bash
copychat [OPTIONS] [PATHS]...

Options:
  -s, --source TEXT     Source to scan (filesystem path, github:owner/repo, or URL)
  -o, --out PATH        Write output to file
  -a, --append          Append output instead of overwriting
  -p, --print          Print output to screen
  -v, --verbose         Show detailed file information in output
  -i, --include TEXT    Extensions to include (comma-separated, e.g. 'py,js,ts')
  -x, --exclude TEXT    Glob patterns to exclude
  -d, --depth INTEGER   Maximum directory depth to scan (0 = current dir only)
  --diff-mode TEXT     How to handle git diffs
  --diff-branch TEXT Compare changes against specified branch
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

## Using `.ccignore` Files

CopyChat supports hierarchical ignore patterns through `.ccignore` files. These files work similarly to `.gitignore` files but with an important difference: they apply to all directories and subdirectories where they're located.

### Key Features

- `.ccignore` files use the same syntax as `.gitignore` files
- Each `.ccignore` file applies to its directory and all subdirectories
- Patterns from multiple `.ccignore` files are inherited, with more specific directories taking precedence

### Example

```
project/
├── .ccignore        # Contains "*.log" - excludes log files in all directories
├── src/
│   ├── .ccignore    # Contains "*.tmp" - excludes tmp files in src/ and below
│   └── ...
└── tests/
    ├── .ccignore    # Contains "*.fixture" - excludes fixture files in tests/ and below
    └── ...
```

In this example:
- `*.log` files are excluded everywhere
- `*.tmp` files are only excluded in `src/` and its subdirectories
- `*.fixture` files are only excluded in `tests/` and its subdirectories

### Creating a `.ccignore` File

Create a `.ccignore` file in your project root or any subdirectory:

```
# Comment lines start with #
# Blank lines are ignored

# Ignore all files with .log extension
*.log

# Ignore specific files
secrets.json
credentials.yaml

# Ignore directories
node_modules/
__pycache__/
```
