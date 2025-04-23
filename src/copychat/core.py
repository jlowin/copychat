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

    # Get gitignore and ccignore specs once for all paths
    git_spec = get_gitignore_spec(base_path)
    cc_spec = get_ccignore_spec(base_path)

    for path in paths:
        if is_glob_pattern(path):
            matches = list(base_path.glob(path))
            # Filter matches through gitignore and ccignore
            for match in matches:
                try:
                    # Check if under base path
                    rel_path = match.relative_to(base_path)
                    # Skip if matches gitignore or ccignore patterns
                    rel_path_str = str(rel_path)
                    if git_spec.match_file(rel_path_str) or cc_spec.match_file(
                        rel_path_str
                    ):
                        continue
                    resolved.append(match)
                except ValueError:
                    # If path is not relative to base_path, just use it as-is
                    resolved.append(match)
        else:
            # For non-glob paths, use them as-is
            path_obj = Path(path)
            if path_obj.is_absolute():
                resolved.append(path_obj)
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


def find_ccignore_files(start_path: Path) -> list[tuple[Path, Path]]:
    """
    Find all .ccignore files that apply to the given path.

    Returns a list of tuples (ccignore_file, directory) where:
    - ccignore_file is the path to the .ccignore file
    - directory is the directory containing the .ccignore file

    The list is ordered from most specific (closest to start_path) to most general.
    """
    ccignore_files = []
    current = start_path.absolute()

    # Start from the given path and traverse up to the root
    while current != current.parent:
        ccignore = current / ".ccignore"
        if ccignore.is_file():
            ccignore_files.append((ccignore, current))
        current = current.parent

    return ccignore_files


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


def get_ccignore_spec(
    path: Path, extra_patterns: Optional[list[str]] = None
) -> pathspec.PathSpec:
    """
    Load .ccignore patterns from all applicable directories.

    This function finds all .ccignore files that apply to the given path,
    from the most specific (closest to the path) to the most general (root).
    Patterns from more specific .ccignore files take precedence over more general ones.
    """
    patterns = []

    # Add any extra patterns provided
    if extra_patterns:
        patterns.extend(extra_patterns)

    # Get all applicable .ccignore files
    ccignore_files = find_ccignore_files(path)

    # Process files from most general to most specific
    # This way, more specific patterns override more general ones
    for ccignore_path, dir_path in reversed(ccignore_files):
        with open(ccignore_path) as f:
            ccignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            patterns.extend(ccignore_patterns)

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def get_git_diff(path: Path, compare_branch: Optional[str] = None) -> str:
    """Get git diff for the given path, optionally comparing against a specific branch."""
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

        # Get the diff, either against the index (default) or specified branch
        if compare_branch:
            # First get the merge base
            merge_base = subprocess.run(
                ["git", "merge-base", "HEAD", compare_branch],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            # Then do the diff against the merge base
            result = subprocess.run(
                ["git", "diff", merge_base, "--", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            result = subprocess.run(
                ["git", "diff", "--", str(path)],  # Removed --exit-code
                capture_output=True,
                text=True,
                check=False,
            )
        return result.stdout  # Return output regardless of return code

    except subprocess.CalledProcessError:
        return ""


def get_changed_files(compare_branch: Optional[str] = None) -> set[Path]:
    """Get set of files that have changes according to git."""
    try:
        # First get the git root directory
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        git_root_path = Path(git_root)

        if compare_branch:
            # Get all changes between current branch and compare branch
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--name-status",
                    f"{compare_branch}...HEAD",  # Use triple dot to compare branches
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            # Also get any unstaged/uncommitted changes
            unstaged_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Combine both results
            combined_output = result.stdout + unstaged_result.stdout
        else:
            # Get both staged and unstaged changes (current behavior)
            combined_output = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout

        changed = set()
        for line in combined_output.splitlines():
            if not line.strip():
                continue

            # Split on tab or space to handle both formats
            parts = line.split(None, 1)  # Split on whitespace, max 1 split
            if len(parts) < 2:
                continue

            status, filepath = parts

            # Handle renamed files (they have arrow notation)
            if " -> " in filepath:
                filepath = filepath.split(" -> ")[-1]

            # Convert relative path to absolute using git root
            abs_path = (git_root_path / filepath).resolve()
            changed.add(abs_path)

        return changed
    except subprocess.CalledProcessError:
        return set()


def get_file_content(
    path: Path,
    diff_mode: DiffMode,
    changed_files: Optional[set[Path]] = None,
    compare_branch: Optional[str] = None,
) -> Optional[str]:
    """Get file content based on diff mode."""
    if not path.is_file():
        return None

    # Get content
    content = path.read_text()

    # Return full content immediately if that's what we want
    if diff_mode == DiffMode.FULL:
        return content

    # Check if file has changes and get diff if needed
    if changed_files is not None:
        has_changes = path in changed_files
        # Get diff here so we can use it for all diff modes
        diff = get_git_diff(path, compare_branch) if has_changes else ""
    else:
        # Get diff first, then check if there are changes
        diff = get_git_diff(path, compare_branch)
        has_changes = bool(diff)

    # Handle different modes
    if diff_mode == DiffMode.DIFF_ONLY:
        return diff if has_changes else None
    elif diff_mode == DiffMode.CHANGED_WITH_DIFF:
        if not has_changes:
            return None
        return f"{content}\n\n# Git Diff:\n{diff}"
    elif diff_mode == DiffMode.FULL_WITH_DIFF:
        if not has_changes:
            return content
        return f"{content}\n\n# Git Diff:\n{diff}"

    return None


def scan_directory(
    path: Path,
    include: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    diff_mode: DiffMode = DiffMode.FULL,
    max_depth: Optional[int] = None,
    compare_branch: Optional[str] = None,
) -> dict[Path, str]:
    """Scan directory for files to process."""
    # Get changed files upfront if we're using a diff mode
    changed_files = (
        get_changed_files(compare_branch) if diff_mode != DiffMode.FULL else None
    )

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
            content = get_file_content(
                current_path, diff_mode, changed_files, compare_branch
            )
            if content is not None:
                result[current_path] = content
            continue

        # Convert to absolute path once
        abs_path = current_path.resolve()
        if not abs_path.exists():
            continue

        # Get gitignore spec once for the starting directory
        git_spec = get_gitignore_spec(abs_path, exclude_patterns)

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

            # Get ccignore spec for the current directory (to handle hierarchical patterns)
            cc_spec = get_ccignore_spec(root_path, exclude_patterns)

            # Check if directory should be skipped (via gitignore or ccignore)
            if rel_root:
                dir_path = rel_root + "/"
                if git_spec.match_file(dir_path) or cc_spec.match_file(dir_path):
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

                # Check both gitignore and ccignore patterns
                if git_spec.match_file(rel_path_str) or cc_spec.match_file(
                    rel_path_str
                ):
                    continue

                # Only create Path object if file passes all filters
                file_path = root_path / filename

                # Get content based on diff mode
                content = get_file_content(
                    file_path, diff_mode, changed_files, compare_branch
                )
                if content is not None:
                    result[file_path] = content

    return result


def scan_files(patterns: list[str], root: Path) -> set[Path]:
    """Scan directory for files matching glob patterns."""
    files = set()
    for pattern in patterns:
        files.update(root.glob(pattern))
    return files
