import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
import pyperclip
from enum import Enum
from importlib.metadata import version as get_version
import atexit
import shutil

from .core import (
    scan_directory,
    DiffMode,
    get_file_content,
)
from .format import (
    format_files as format_files_xml,
    create_display_header,
)
from .sources import GitHubSource, GitHubItem, GitHubFile


# Register cleanup of temporary GitHub directory
def _cleanup_github_temp():
    from .sources import _github_temp_dir

    if _github_temp_dir is not None and _github_temp_dir.exists():
        try:
            shutil.rmtree(_github_temp_dir)
        except Exception:
            pass  # Ignore cleanup errors


atexit.register(_cleanup_github_temp)


class SourceType(Enum):
    """Type of source to scan."""

    FILESYSTEM = "filesystem"  # Default
    GITHUB = "github"
    WEB = "web"  # For future use


def parse_source(source: str) -> tuple[SourceType, str]:
    """Parse source string into type and location."""
    import re

    if source.startswith(("github:", "gh:")):
        return SourceType.GITHUB, source.split(":", 1)[1]

    # Handle GitHub URLs with issues/pulls/discussions
    if source and source.startswith(("http://", "https://")) and "github.com" in source:
        pr_issue_match = re.search(
            r"github\.com/([^/]+/[^/]+)/(?:issues|pull|discussions)/([0-9]+)", source
        )
        if pr_issue_match:
            # This is a PR, issue, or discussion URL, keep it as FILESYSTEM type so it's processed directly
            return SourceType.FILESYSTEM, source

        # Handle GitHub blob URLs (individual files)
        blob_match = re.search(r"github\.com/([^/]+/[^/]+)/blob/([^/]+)/(.*)", source)
        if blob_match:
            # This is a GitHub blob URL, keep it as FILESYSTEM type so it's processed directly
            return SourceType.FILESYSTEM, source

    # Regular GitHub repo URL
    if source and "github.com" in source:
        parts = source.split("github.com/", 1)
        if len(parts) == 2:
            return SourceType.GITHUB, parts[1]

    if source and source.startswith(("http://", "https://")):
        return SourceType.WEB, source

    return SourceType.FILESYSTEM, source


def parse_github_item(item: str) -> tuple[str, int, str]:
    """Parse issue, PR, or discussion identifier into repo, number, and type."""
    import re

    if item.startswith("http://") or item.startswith("https://"):
        m = re.search(
            r"github\.com/([^/]+/[^/]+)/(issues|pull|discussions)/([0-9]+)", item
        )
        if not m:
            raise typer.BadParameter("Invalid GitHub URL")
        return (
            m.group(1),
            int(m.group(3)),
            m.group(2).rstrip("s"),
        )  # Remove 's' from 'issues' -> 'issue'

    if "#" in item:
        repo, num = item.split("#", 1)
        return (
            repo.strip(),
            int(num),
            "issue",
        )  # Default to issue for backward compatibility

    raise typer.BadParameter("Item must be in owner/repo#number format or URL")


def parse_github_blob(item: str) -> tuple[str, str, str]:
    """Parse GitHub blob URL into repo, ref, and file path."""
    import re

    match = re.search(r"github\.com/([^/]+/[^/]+)/blob/([^/]+)/(.*)", item)
    if not match:
        raise typer.BadParameter("Invalid GitHub blob URL")

    return match.group(1), match.group(2), match.group(3)  # repo, ref, file_path


def diff_mode_callback(value: str) -> DiffMode:
    """Convert string value to DiffMode enum."""
    try:
        if isinstance(value, DiffMode):
            return value
        return DiffMode(value)
    except ValueError:
        valid_values = [mode.value for mode in DiffMode]
        raise typer.BadParameter(f"Must be one of: {', '.join(valid_values)}")


app = typer.Typer(
    no_args_is_help=True,  # Show help when no args provided
    add_completion=False,  # Disable shell completion for simplicity
)
console = Console()
error_console = Console(stderr=True)


@app.command()
def main(
    paths: list[str] = typer.Argument(
        None,
        help="Paths to process within the source (defaults to current directory)",
    ),
    version: bool = typer.Option(
        None,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Source to scan (filesystem path, github:owner/repo, or URL)",
    ),
    outfile: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Write output to file. If provided, output will not be copied to clipboard.",
    ),
    append: bool = typer.Option(
        False,
        "--append",
        "-a",
        help="Append output instead of overwriting",
    ),
    print_output: bool = typer.Option(
        False,
        "--print",
        "-p",
        help="Print output to screen",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed file information in output",
    ),
    include: Optional[str] = typer.Option(
        None,
        "--include",
        "-i",
        help="Extensions to include (comma-separated, e.g. 'py,js,ts')",
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        "-x",
        help="Glob patterns to exclude",
    ),
    diff_mode: str = typer.Option(
        "full",  # Pass the string value instead of enum
        "--diff-mode",
        help="How to handle git diffs",
        callback=diff_mode_callback,
    ),
    depth: Optional[int] = typer.Option(
        None,
        "--depth",
        "-d",
        help="Maximum directory depth to scan (0 = current dir only)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Debug mode for development",
    ),
    compare_branch: Optional[str] = typer.Option(
        None,
        "--diff-branch",
        help="Compare changes against specified branch instead of working directory",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        envvar="GITHUB_TOKEN",
        help="GitHub token for issue and PR access",
    ),
) -> None:
    """Convert source code files to markdown format for LLM context."""
    if version:
        console.print(f"copychat version {get_version('copychat')}")
        raise typer.Exit()

    try:
        # Parse source type and location
        source_type, source_loc = (
            parse_source(source) if source else (SourceType.FILESYSTEM, ".")
        )

        if debug:
            error_console.print(
                f"[magenta]Source type:[/] {source_type}, location: {source_loc}"
            )
            error_console.print(f"[magenta]Paths to process:[/] {paths}")

        # Handle different source types
        if source_type == SourceType.GITHUB:
            try:
                github_source = GitHubSource(source_loc)
                source_dir = github_source.fetch()
            except Exception as e:
                if debug:
                    raise
                error_console.print(
                    f"[red]Error fetching GitHub repository:[/] {str(e)}"
                )
                raise typer.Exit(1)
        elif source_type == SourceType.WEB:
            error_console.print("[red]Web sources not yet implemented[/]")
            raise typer.Exit(1)
        else:
            source_dir = Path(source_loc)

        # Handle file vs directory source
        if source_dir.is_file():
            content = get_file_content(
                source_dir, diff_mode, compare_branch=compare_branch
            )
            all_files = {source_dir: content} if content is not None else {}
        else:
            # For directories, scan all paths
            if not paths:
                paths = ["."]

            # Handle paths
            all_files = {}
            for path in paths:
                if debug:
                    error_console.print(f"[cyan]Processing path:[/] {path}")

                # Allow GitHub issues/PRs/discussions as direct arguments
                try:
                    repo, num, item_type = parse_github_item(path)
                    if debug:
                        error_console.print(
                            f"[blue]Processing GitHub {item_type}:[/] {repo}#{num}"
                        )
                    gh_item = GitHubItem(repo, num, token, item_type)
                    p, content = gh_item.fetch()
                    all_files[p] = content
                    if debug:
                        error_console.print(
                            f"[green]Successfully fetched GitHub {item_type}[/]"
                        )
                    continue
                except Exception as e:
                    if debug:
                        error_console.print(
                            f"[yellow]Failed to process as GitHub item:[/] {str(e)}"
                        )
                    pass

                # Allow GitHub blob URLs (individual files)
                try:
                    repo, ref, file_path = parse_github_blob(path)
                    if debug:
                        error_console.print(
                            f"[blue]Processing GitHub file:[/] {repo}/{file_path}@{ref}"
                        )
                    gh_file = GitHubFile(path, token)
                    p, content = gh_file.fetch()
                    all_files[p] = content
                    if debug:
                        error_console.print(
                            "[green]Successfully fetched GitHub file[/]"
                        )
                    continue
                except Exception as e:
                    if debug:
                        error_console.print(
                            f"[yellow]Failed to process as GitHub blob:[/] {str(e)}"
                        )
                    pass

                target = Path(path)
                if target.is_absolute():
                    # Use absolute paths as-is
                    if target.is_file():
                        content = get_file_content(
                            target, diff_mode, compare_branch=compare_branch
                        )
                        if content is not None:
                            all_files[target] = content
                    else:
                        files = scan_directory(
                            target,
                            include=include.split(",") if include else None,
                            exclude_patterns=exclude,
                            diff_mode=diff_mode,
                            max_depth=depth,
                            compare_branch=compare_branch,
                        )
                        all_files.update(files)
                else:
                    # For relative paths, try source dir first, then current dir
                    targets = []
                    if source_type == SourceType.GITHUB:
                        # For GitHub sources, only look in the source directory
                        targets = [source_dir / path]
                    else:
                        # For filesystem sources, try both but prefer source dir
                        if source_dir != Path("."):
                            targets.append(source_dir / path)
                        targets.append(Path.cwd() / path)

                    for target in targets:
                        if target.exists():
                            if target.is_file():
                                content = get_file_content(
                                    target, diff_mode, compare_branch=compare_branch
                                )
                                if content is not None:
                                    all_files[target] = content
                                break
                            else:
                                files = scan_directory(
                                    target,
                                    include=include.split(",") if include else None,
                                    exclude_patterns=exclude,
                                    diff_mode=diff_mode,
                                    max_depth=depth,
                                    compare_branch=compare_branch,
                                )
                                all_files.update(files)
                                break
        if not all_files:
            error_console.print("Found [red]0[/] matching files")
            return

        # Separate GitHub issues/PRs from regular files for better reporting
        github_items = []
        filesystem_files = []

        for path, content in all_files.items():
            if (
                str(path).endswith((".md", ".issue.md", ".pr.md", ".discussion.md"))
                and isinstance(path, Path)
                and not path.exists()
            ) or (
                # Also detect GitHub files by checking if the filename contains repo info and doesn't exist locally
                isinstance(path, Path)
                and not path.exists()
                and "_"
                in str(
                    path.name
                )  # GitHub files have underscores from repo/ref/path formatting
                and any(part in str(path.name) for part in ["github", "blob", "_"])
            ):
                github_items.append((path, content))
            else:
                filesystem_files.append((path, content))

        # Format files - pass both paths and content
        format_result = format_files_xml(
            [(path, content) for path, content in all_files.items()]
        )

        # Get the formatted content, conditionally including header
        if verbose:
            result = str(format_result)
            # Print the display header to stderr for visibility
            error_console.print(
                "\nFile summary:",
                style="bold blue",
            )
            # Use the display-friendly header
            error_console.print(create_display_header(format_result))
            error_console.print()  # Add blank line after header
        else:
            # Skip the header by taking only the formatted files
            result = "\n".join(f.formatted_content for f in format_result.files)

        # Custom message based on content types
        if github_items and filesystem_files:
            error_console.print(
                f"Downloaded [green]{len(github_items)}[/] GitHub items and found [green]{len(filesystem_files)}[/] matching files"
            )
        elif github_items:
            error_console.print(
                f"Downloaded [green]{len(github_items)}[/] GitHub {'item' if len(github_items) == 1 else 'items'}"
            )
        else:
            error_console.print(
                f"Found [green]{len(format_result.files)}[/] matching files"
            )

        # Handle outputs
        if outfile:
            if append and outfile.exists():
                existing_content = outfile.read_text()
                result = existing_content + "\n\n" + result
            outfile.write_text(result)
            error_console.print(
                f"Output {'appended' if append else 'written'} to [green]{outfile}[/]"
            )
        # Only use clipboard if not writing to file AND not just printing to stdout
        elif not print_output or append:
            if append:
                try:
                    existing_clipboard = pyperclip.paste()
                    result = existing_clipboard + "\n\n" + result
                except Exception:
                    error_console.print(
                        "[yellow]Warning: Could not read clipboard for append[/]"
                    )

            try:
                pyperclip.copy(result)
                # Calculate total lines outside the f-string
                total_lines = sum(
                    f.content.count("\n") + 1 for f in format_result.files
                )
                error_console.print(
                    f"{'Appended' if append else 'Copied'} to clipboard "
                    f"(~{format_result.total_tokens:,} tokens, {total_lines:,} lines)"
                )
            except Exception as e:
                error_console.print(
                    f"[yellow]Warning: Could not copy to clipboard: {str(e)}[/]"
                )
                if not print_output:
                    # If clipboard failed and we're not printing, show the content
                    error_console.print("[cyan]Content would have been:[/]")
                    print(result)

        # Print to stdout only if explicitly requested
        if print_output:
            print(result)

    except Exception as e:
        if debug:
            raise
        error_console.print(f"[red]Error:[/] {str(e)}")
        raise typer.Exit(1)
