from pathlib import Path
from typing import Optional
import pathspec
import subprocess
from enum import Enum
import os

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
    base_path = base_path.resolve()

    # Get gitignore spec once for all paths
    spec = get_gitignore_spec(base_path)

    for path in paths:
        if is_glob_pattern(path):
            matches = list(base_path.glob(path))
            # Filter matches through gitignore and base path checks
            for match in matches:
                try:
                    # Check if under base path
                    rel_path = match.relative_to(base_path)
                    # Skip if matches gitignore patterns
                    if spec.match_file(str(rel_path)):
                        continue
                    resolved.append(match)
                except ValueError:
                    continue
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


def get_changed_files() -> set[Path]:
    """Get set of files that have changes according to git."""
    try:
        # Get both staged and unstaged changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        changed = set()
        for line in result.stdout.splitlines():
            if line.strip() and len(line) > 3:
                # Extract filename from git status output
                filepath = line[3:].strip().split(" -> ")[-1]
                changed.add(Path(filepath))
        return changed
    except subprocess.CalledProcessError:
        return set()


def get_file_content(
    path: Path, diff_mode: DiffMode, changed_files: Optional[set[Path]] = None
) -> Optional[str]:
    """Get file content based on diff mode."""
    if not path.is_file():
        return None

    # Get content
    content = path.read_text()

    # Only get diff if needed based on mode
    if diff_mode in (DiffMode.FULL, DiffMode.DIFF_ONLY):
        return content if diff_mode == DiffMode.FULL else None

    # For diff modes, first check if file is in changed set
    if changed_files is not None:
        has_changes = path in changed_files
    else:
        # Fallback to individual diff check
        diff = get_git_diff(path)
        has_changes = bool(diff)

    # Handle different modes
    if diff_mode == DiffMode.CHANGED_WITH_DIFF:
        if not has_changes:
            return None
        diff = get_git_diff(path) if changed_files is not None else diff
        return f"{content}\n\n# Git Diff:\n{diff}"
    elif diff_mode == DiffMode.FULL_WITH_DIFF:
        if not has_changes:
            return content
        diff = get_git_diff(path) if changed_files is not None else diff
        return f"{content}\n\n# Git Diff:\n{diff}"

    return None


def scan_directory(
    path: Path,
    include: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    diff_mode: DiffMode = DiffMode.FULL,
    max_depth: Optional[int] = None,
) -> dict[Path, str]:
    """Scan directory for files to process."""
    # Get changed files upfront if we're using a diff mode
    changed_files = get_changed_files() if diff_mode != DiffMode.FULL else None

    # Convert string paths to Path objects and handle globs
    if isinstance(path, str):
        if is_glob_pattern(path):
            paths = resolve_paths([path])
        else:
            paths = [Path(path)]
    else:
        paths = [path]

    result = {}

    # Pre-compute extension set
    include_set = {f".{ext.lstrip('.')}" for ext in (include or DEFAULT_EXTENSIONS)}

    for current_path in paths:
        if current_path.is_file():
            # For single files, just check if it matches filters
            if include and current_path.suffix.lstrip(".") not in include:
                continue
            content = get_file_content(current_path, diff_mode, changed_files)
            if content is not None:
                result[current_path] = content
            continue

        # Convert to absolute path once
        abs_path = current_path.resolve()
        if not abs_path.exists():
            continue

        # Get gitignore spec once per directory
        spec = get_gitignore_spec(abs_path, exclude_patterns)

        # Use os.walk for better performance than rglob
        for root, _, files in os.walk(abs_path):
            root_path = Path(root)

            # Check depth if max_depth is specified
            if max_depth is not None:
                try:
                    # Calculate current depth relative to the starting path
                    rel_path = root_path.relative_to(abs_path)
                    current_depth = len(rel_path.parts)
                    if current_depth > max_depth:
                        continue
                except ValueError:
                    continue

            # Get relative path once per directory
            try:
                rel_root = str(root_path.relative_to(abs_path))
                if rel_root == ".":
                    rel_root = ""
            except ValueError:
                continue

            # Check if directory should be skipped
            if rel_root and spec.match_file(rel_root + "/"):
                continue

            for filename in files:
                # Quick extension check before more expensive operations
                ext = Path(filename).suffix.lower()
                if ext not in include_set:
                    continue

                # Build relative path string directly
                rel_path_str = (
                    os.path.join(rel_root, filename) if rel_root else filename
                )

                # Check gitignore patterns
                if spec.match_file(rel_path_str):
                    continue

                # Only create Path object if file passes all filters
                file_path = root_path / filename

                # Get content based on diff mode
                content = get_file_content(file_path, diff_mode, changed_files)
                if content is not None:
                    result[file_path] = content

    return result


def scan_files(patterns: list[str], root: Path) -> set[Path]:
    """Scan directory for files matching glob patterns."""
    files = set()
    for pattern in patterns:
        files.update(root.glob(pattern))
    return files
