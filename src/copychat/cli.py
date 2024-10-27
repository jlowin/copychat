import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
import pyperclip
from enum import Enum

from .core import scan_directory, DiffMode
from .format import (
    estimate_tokens,
    format_files as format_files_xml,
)
from .sources import GitHubSource


class SourceType(Enum):
    """Type of source to scan."""

    FILESYSTEM = "filesystem"  # Default
    GITHUB = "github"
    WEB = "web"  # For future use


def parse_source(source: str) -> tuple[SourceType, str]:
    """Parse source string into type and location."""
    if source.startswith(("github:", "gh:")):
        return SourceType.GITHUB, source.split(":", 1)[1]
    if source.startswith(("http://", "https://")):
        return SourceType.WEB, source
    if "github.com" in source:
        # Handle raw GitHub URLs
        parts = source.split("github.com/", 1)
        if len(parts) == 2:
            return SourceType.GITHUB, parts[1]
    return SourceType.FILESYSTEM, source


def diff_mode_callback(value: str) -> DiffMode:
    """Convert string value to DiffMode enum."""
    try:
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
        help="Write output to file",
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
    diff_mode: DiffMode = typer.Option(
        DiffMode.FULL.value,
        "--diff-mode",
        "-d",
        help="How to handle git diffs",
        callback=diff_mode_callback,
    ),
) -> None:
    """Convert source code files to markdown format for LLM context."""
    try:
        # Parse source type and location
        source_type, source_loc = (
            parse_source(source) if source else (SourceType.FILESYSTEM, ".")
        )

        # Handle different source types
        if source_type == SourceType.GITHUB:
            try:
                github_source = GitHubSource(source_loc)
                source_dir = github_source.fetch()
            except Exception as e:
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
            all_files = {source_dir: None}  # Use None as placeholder for git info
        else:
            # For directories, scan all paths
            if not paths:
                paths = ["."]

            # Scan all paths within the source
            all_files = {}
            for path in paths:
                target = source_dir / path if source_dir != Path(".") else Path(path)
                if target.is_file():
                    all_files[target] = None
                else:
                    files = scan_directory(
                        target,
                        include=include,
                        exclude_patterns=exclude,
                        diff_mode=diff_mode,
                    )
                    all_files.update(files)

        if not all_files:
            error_console.print("[yellow]No matching files found[/]")
            raise typer.Exit(1)

        # Format files
        result = format_files_xml(list(all_files.keys()))

        # Handle outputs
        if outfile:
            if append and outfile.exists():
                existing_content = outfile.read_text()
                result = existing_content + "\n\n" + result
            outfile.write_text(result)
            error_console.print(
                f"Output {'appended' if append else 'written'} to [green]{outfile}[/]"
            )

        # Handle clipboard
        if append:
            try:
                existing_clipboard = pyperclip.paste()
                result = existing_clipboard + "\n\n" + result
            except Exception:
                error_console.print(
                    "[yellow]Warning: Could not read clipboard for append[/]"
                )

        pyperclip.copy(result)
        token_count = estimate_tokens(result)
        error_console.print(
            f"[green]{'Appended' if append else 'Copied'}[/] {len(all_files)} files to clipboard "
            f"({len(result):,} chars, ~{token_count:,} tokens)"
        )

        # Print to stdout only if explicitly requested
        if print_output:
            print(result)

    except Exception as e:
        error_console.print(f"[red]Error:[/] {str(e)}")
        raise typer.Exit(1)
