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


def is_glob_pattern(path: str) -> bool:
    """Check if a path contains glob patterns."""
    return "*" in path


def resolve_paths(paths: list[str], base_path: Path = Path(".")) -> list[Path]:
    """Resolve a mix of glob patterns and regular paths."""
    resolved = []
    for path in paths:
        if is_glob_pattern(path):
            # Use Path.rglob() for better handling of recursive glob patterns
            matches = list(base_path.rglob(path))
            resolved.extend(matches)
        else:
            resolved.append(base_path / path)
    return resolved


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
    # Convert string paths to Path objects and handle globs
    if isinstance(path, str):
        if is_glob_pattern(path):
            paths = resolve_paths([path])
        else:
            paths = [Path(path)]
    else:
        paths = [path]

    result = {}

    for current_path in paths:
        if current_path.is_file():
            # For single files, just check if it matches filters
            if include and current_path.suffix.lstrip(".") not in include:
                continue
            content = get_file_content(current_path, diff_mode)
            if content is not None:
                result[current_path] = content
            continue

        # Convert to absolute path
        abs_path = current_path.resolve()
        if not abs_path.exists():
            continue

        # Use provided extensions or defaults
        include_set = {f".{ext.lstrip('.')}" for ext in (include or DEFAULT_EXTENSIONS)}

        # Get combined gitignore and default exclusions
        spec = get_gitignore_spec(abs_path, exclude_patterns)

        for file_path in abs_path.rglob("*"):
            # Skip non-files
            if not file_path.is_file():
                continue

            # Get relative path for pattern matching
            try:
                rel_path = file_path.relative_to(abs_path)
            except ValueError:
                # If no common path, skip this file
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
