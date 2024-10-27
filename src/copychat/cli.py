import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
import pyperclip

from .core import scan_directory, DiffMode  # Import DiffMode from core
from .patterns import DEFAULT_EXTENSIONS
from .format import (
    estimate_tokens,
    format_files as format_files_xml,
)  # Rename import to avoid confusion


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
    source: list[Path] = typer.Argument(
        None,
        help="Source directories to process (defaults to current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    outfile: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Write output to file",
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
        DiffMode.FULL.value,  # Use the string value as default
        "--diff-mode",
        "-d",
        help="How to handle git diffs",
        callback=diff_mode_callback,  # Convert string to enum
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output",
    ),
) -> None:
    """Convert source code files to markdown format for LLM context."""
    try:
        source_dirs = source if source else [Path.cwd()]
        include_exts = include.split(",") if include else list(DEFAULT_EXTENSIONS)

        # Scan all directories and combine results
        all_files = {}
        for directory in source_dirs:
            files = scan_directory(
                directory,
                include=include_exts,
                extra_patterns=exclude,
                diff_mode=diff_mode,
                verbose=verbose,
            )
            all_files.update(files)

        if not all_files:
            error_console.print("[yellow]No matching files found[/]")  # Keep using Rich
            raise typer.Exit(1)

        # Format files
        result = format_files_xml(list(all_files.keys()), verbose=verbose)

        # Handle outputs
        if outfile:
            outfile.write_text(result)
            error_console.print(f"Output written to [green]{outfile}[/]")

        # Always copy to clipboard by default
        pyperclip.copy(result)
        token_count = estimate_tokens(result)
        error_console.print(
            f"[green]Copied[/] {len(all_files)} files to clipboard "
            f"({len(result):,} chars, ~{token_count:,} tokens)"
        )

        # Print to stdout only if explicitly requested
        if print_output:
            print(result)

    except Exception as e:
        error_console.print(f"[red]Error:[/] {str(e)}")
        raise typer.Exit(1)
