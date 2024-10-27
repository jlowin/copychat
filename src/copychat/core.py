from pathlib import Path
from typing import Optional
import pathspec
import sys
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
    print(f"Searching for gitignore from: {start_path}", file=sys.stderr)
    current = start_path.absolute()
    while current != current.parent:
        gitignore = current / ".gitignore"
        if gitignore.is_file():
            print(f"Found gitignore at: {gitignore}", file=sys.stderr)
            return gitignore
        current = current.parent
    print("No gitignore found", file=sys.stderr)
    return None


def get_gitignore_spec(
    path: Path, extra_patterns: Optional[list[str]] = None, verbose: bool = False
) -> pathspec.PathSpec:
    """Load .gitignore patterns and combine with our default exclusions."""
    if verbose:
        print(f"Getting gitignore spec for: {path}", file=sys.stderr)

    patterns = list(EXCLUDED_PATTERNS)
    if verbose:
        print(f"Added {len(EXCLUDED_PATTERNS)} default patterns", file=sys.stderr)

    # Add directory exclusions
    dir_patterns = [f"{d}/" for d in EXCLUDED_DIRS]
    patterns.extend(dir_patterns)
    if verbose:
        print(f"Added {len(dir_patterns)} directory exclusions", file=sys.stderr)

    # Add any extra patterns provided
    if extra_patterns:
        patterns.extend(extra_patterns)
        if verbose:
            print(f"Added {len(extra_patterns)} extra patterns", file=sys.stderr)

    # Add patterns from .gitignore if found
    gitignore_path = find_gitignore(path) if verbose else None
    if gitignore_path:
        with open(gitignore_path) as f:
            gitignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            patterns.extend(gitignore_patterns)
            if verbose:
                print(
                    f"Added {len(gitignore_patterns)} patterns from gitignore",
                    file=sys.stderr,
                )

    if verbose:
        print(f"Total patterns: {len(patterns)}", file=sys.stderr)
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def get_git_diff(path: Path, verbose: bool = False) -> str:
    """Get git diff for the given path."""
    try:
        result = subprocess.run(
            ["git", "diff", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"Error getting git diff: {e}", file=sys.stderr)
        return ""


def get_file_content(
    path: Path, diff_mode: DiffMode, verbose: bool = False
) -> Optional[str]:
    """
    Get file content based on diff mode.
    Returns None if file should be skipped.
    """
    if diff_mode == DiffMode.FULL:
        return path.read_text()

    diff = get_git_diff(path, verbose)

    if not diff and diff_mode in (DiffMode.CHANGED_WITH_DIFF, DiffMode.DIFF_ONLY):
        return None

    if diff_mode == DiffMode.DIFF_ONLY:
        return diff

    # For FULL_WITH_DIFF and CHANGED_WITH_DIFF, we return the file content
    # with diff markers if there are changes
    content = path.read_text()
    return f"{content}\n\nDiff:\n{diff}" if diff else content


def scan_directory(
    path: Path,
    include: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    diff_mode: DiffMode = DiffMode.FULL,
    verbose: bool = False,
) -> dict[Path, Optional[str]]:
    """Scan directory for files to process.

    Args:
        path: Path to scan (can be file or directory)
        include: List of extensions to include
        exclude_patterns: Additional glob patterns to exclude
        diff_mode: How to handle git diffs
        verbose: Show verbose output

    Returns:
        Dictionary mapping file paths to git diff info (if any)
    """
    if path.is_file():
        # For single files, just check if it matches filters
        if include and path.suffix.lstrip(".") not in include:
            return {}
        return {path: None}

    # Convert to absolute path first
    abs_path = path.absolute()

    if verbose:
        print(f"\nScanning directory: {abs_path}", file=sys.stderr)

    if not abs_path.is_dir():
        raise ValueError(f"Path {abs_path} is not a directory")

    # Use provided extensions or defaults
    include_set = {f".{ext.lstrip('.')}" for ext in (include or DEFAULT_EXTENSIONS)}

    if verbose:
        print(f"Include extensions: {include_set}", file=sys.stderr)

    # Get combined gitignore and default exclusions
    spec = get_gitignore_spec(abs_path, exclude_patterns, verbose)

    result = {}
    processed = 0
    skipped = 0

    if verbose:
        print("\nStarting file scan...", file=sys.stderr)

    for file_path in abs_path.rglob("*"):
        processed += 1
        if verbose and processed % 100 == 0:
            print(
                f"Processed {processed} files, found {len(result)}, skipped {skipped}...",
                file=sys.stderr,
            )

        # Skip non-files
        if not file_path.is_file():
            skipped += 1
            continue

        # Get relative path for pattern matching
        try:
            rel_path = file_path.relative_to(abs_path)
        except ValueError:
            skipped += 1
            continue

        # Skip excluded patterns
        if spec.match_file(str(rel_path)):
            skipped += 1
            continue

        # Apply extension filters
        ext = file_path.suffix.lower()
        if ext not in include_set:
            skipped += 1
            continue

        content = get_file_content(file_path, diff_mode, verbose)
        if content is not None:
            result[file_path] = content

    if verbose:
        print(
            f"\nScan complete: processed {processed} files, found {len(result)}, skipped {skipped}",
            file=sys.stderr,
        )
    return result
