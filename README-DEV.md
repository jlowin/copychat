# copychat development notes

Internal development notes and goals for the copychat library. This document is for developer reference only.

## Core functionality

The library takes a source directory and produces a markdown representation of all relevant code files, either copying to clipboard or saving to a file.

### Key features

- Scan directory recursively for code files
- Smart filtering using .gitignore if available
- CLI interface with typer/rich for great UX
- Configurable file extension inclusion/exclusion
- Output to clipboard (default) or file
- XML-style markdown formatting

### Output format

Each file will be formatted in markdown like:

```xml
<file path="path/to/file.py" language="python">
def example():
    pass
</file>
```

## Technical decisions

### Dependencies

- typer - CLI interface
- rich - Terminal formatting
- pyperclip - Clipboard interaction
- pathspec - .gitignore parsing
- tomli - pyproject.toml parsing (if needed)

### Project structure

```
copychat/
├── pyproject.toml      # Project metadata and dependencies
├── src/
│   └── copychat/    
│       ├── __init__.py
│       ├── cli.py      # Typer CLI implementation
│       ├── core.py     # Core scanning/processing logic
│       └── format.py   # Markdown formatting utilities
└── tests/
    └── test_*.py      # Test files
```

### Development roadmap

1. Basic file scanning with extension filtering
2. Gitignore integration
3. Markdown formatting
4. Clipboard/file output handling
5. CLI implementation
6. Testing and documentation

### Notes

- Keep the core logic separate from CLI for better testing
- Use pathlib for cross-platform path handling
- Consider adding a config file option later for project-specific settings
- May want to add file size limits and warnings
- Consider adding syntax highlighting hints in markdown
- Add support for detecting file language based on extension
- Consider adding a way to exclude specific files/patterns beyond gitignore
