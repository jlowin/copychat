from pathlib import Path
from typing import Optional
import pathspec
import subprocess
from enum import Enum

from .patterns import DEFAULT_EXTENSIONS, EXCLUDED_DIRS, EXCLUDED_PATTERNS


class DiffMode(Enum):
    FULL = "full"  # All files as-is
    FULL_WITH_DIFF = "full-with-diff"  # All files with diff markers
    CHANGED_WITH_DIFF = "changed-with-diff"  # Only changed files with diff markers
    DIFF_ONLY = "diff-only"  # Only the diff chunks


def find_gitignore(start_path: Path) -> Optional[Path]:
    """Search for .gitignore file in current and parent directories."""
    current = start_path.absolute()
    while current != current.parent:
        gitignore = current / ".gitignore"
        if gitignore.is_file():
            return gitignore
        current = current.parent
    return None


def get_gitignore_spec(
    path: Path, extra_patterns: Optional[list[str]] = None
) -> pathspec.PathSpec:
    """Load .gitignore patterns and combine with our default exclusions."""
    patterns = list(EXCLUDED_PATTERNS)

    # Add directory exclusions
    dir_patterns = [f"{d}/" for d in EXCLUDED_DIRS]
    patterns.extend(dir_patterns)

    # Add any extra patterns provided
    if extra_patterns:
        patterns.extend(extra_patterns)

    # Add patterns from .gitignore if found
    gitignore_path = find_gitignore(path)
    if gitignore_path:
        with open(gitignore_path) as f:
            gitignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            patterns.extend(gitignore_patterns)

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def get_git_diff(path: Path) -> str:
    """Get git diff for the given path."""
    try:
        # First check if file is tracked by git
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            capture_output=True,
            text=True,
            check=False,  # Don't raise error for untracked files
        )
        if result.returncode != 0:
            return ""  # File is not tracked by git

        # Get the diff for tracked files
        result = subprocess.run(
            ["git", "diff", "--exit-code", str(path)],
            capture_output=True,
            text=True,
            check=False,  # Don't raise error for no changes
        )
        # exit-code 0 means no changes, 1 means changes present
        return result.stdout if result.returncode == 1 else ""

    except subprocess.CalledProcessError:
        return ""


def get_file_content(path: Path, diff_mode: DiffMode) -> Optional[str]:
    """Get file content based on diff mode."""
    if not path.is_file():
        return None

    # Get content and diff
    content = path.read_text()
    diff = get_git_diff(path)

    # Handle different modes
    if diff_mode == DiffMode.FULL:
        return content
    elif diff_mode == DiffMode.FULL_WITH_DIFF:
        return f"{content}\n\n# Git Diff:\n{diff}" if diff else content
    elif diff_mode == DiffMode.CHANGED_WITH_DIFF:
        return f"{content}\n\n# Git Diff:\n{diff}" if diff else None
    elif diff_mode == DiffMode.DIFF_ONLY:
        return diff if diff else None
    else:
        return None  # Shouldn't reach here, but makes mypy happy


def scan_directory(
    path: Path,
    include: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    diff_mode: DiffMode = DiffMode.FULL,
) -> dict[Path, str]:
    """Scan directory for files to process."""
    if path.is_file():
        # For single files, just check if it matches filters
        if include and path.suffix.lstrip(".") not in include:
            return {}
        content = get_file_content(path, diff_mode)
        return {path: content} if content is not None else {}

    # Convert to absolute path first
    abs_path = path.absolute()

    if not abs_path.is_dir():
        raise ValueError(f"Path {abs_path} is not a directory")

    # Use provided extensions or defaults
    include_set = {f".{ext.lstrip('.')}" for ext in (include or DEFAULT_EXTENSIONS)}

    # Get combined gitignore and default exclusions
    spec = get_gitignore_spec(abs_path, exclude_patterns)

    result = {}

    for file_path in abs_path.rglob("*"):
        # Skip non-files
        if not file_path.is_file():
            continue

        # Get relative path for pattern matching
        try:
            rel_path = file_path.relative_to(abs_path)
        except ValueError:
            continue

        # Skip excluded patterns
        if spec.match_file(str(rel_path)):
            continue

        # Apply extension filters
        ext = file_path.suffix.lower()
        if ext not in include_set:
            continue

        # Get content based on diff mode
        content = get_file_content(file_path, diff_mode)
        if content is not None:
            result[file_path] = content

    return result
