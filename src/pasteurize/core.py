from pathlib import Path
from typing import Optional, Sequence
import pathspec
import sys

from .patterns import DEFAULT_EXTENSIONS, EXCLUDED_DIRS, EXCLUDED_PATTERNS


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


def scan_directory(
    path: Path,
    include: Optional[Sequence[str]] = None,
    extra_patterns: Optional[list[str]] = None,
    verbose: bool = False,
) -> list[Path]:
    """
    Scan directory for relevant files.

    Args:
        path: Directory to scan
        include: File extensions to include (without dots)
        extra_patterns: Additional gitignore-style patterns to exclude
        verbose: Whether to print debug information

    Returns:
        List of paths to relevant files
    """
    if verbose:
        print(f"\nScanning directory: {path}", file=sys.stderr)

    if not path.is_dir():
        raise ValueError(f"Path {path} is not a directory")

    # Use provided extensions or defaults
    include_set = {f".{ext.lstrip('.')}" for ext in (include or DEFAULT_EXTENSIONS)}

    if verbose:
        print(f"Include extensions: {include_set}", file=sys.stderr)

    # Get combined gitignore and default exclusions
    spec = get_gitignore_spec(path, extra_patterns, verbose)

    result = []
    processed = 0
    skipped = 0

    if verbose:
        print("\nStarting file scan...", file=sys.stderr)

    for file_path in path.rglob("*"):
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
            rel_path = file_path.relative_to(path)
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

        result.append(file_path)

    if verbose:
        print(
            f"\nScan complete: processed {processed} files, found {len(result)}, skipped {skipped}",
            file=sys.stderr,
        )
    return sorted(result)
