import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
import pyperclip

from .core import scan_directory
from .format import format_files
from .patterns import DEFAULT_EXTENSIONS

app = typer.Typer(
    no_args_is_help=True,  # Show help when no args provided
    add_completion=False,  # Disable shell completion for simplicity
)
console = Console()


@app.command()
def main(
    source: list[Path] = typer.Argument(
        ...,
        help="Source directories to process",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    outfile: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output file path (defaults to clipboard)",
    ),
    include: Optional[str] = typer.Option(
        None,
        "--include",
        "-i",
        help="Extensions to include (comma-separated, e.g. 'py,js,ts'). "
        "If not specified, uses default extensions.",
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        "-x",
        help="Glob patterns to exclude (can be used multiple times). Examples:\n"
        "--exclude '*.test.js' = exclude test files\n"
        "--exclude '**/tests/**' = exclude tests directories\n"
        "--exclude 'src/legacy/**' = exclude legacy directory\n"
        "--exclude '*.min.js' = exclude minified JS",
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
        if verbose:
            console.print(f"Scanning directories: {', '.join(str(s) for s in source)}")

            if include:
                console.print(f"Including extensions: {include}")
            else:
                console.print(
                    f"Using default extensions: {','.join(sorted(DEFAULT_EXTENSIONS))}"
                )

            if exclude:
                console.print(f"Exclude patterns: {', '.join(exclude)}")

        # Process include extensions - if specified, use only those
        include_exts = include.split(",") if include else list(DEFAULT_EXTENSIONS)

        # Scan all directories and combine results
        all_files = []
        for directory in source:
            files = scan_directory(
                directory,
                include=include_exts,
                extra_patterns=exclude,
                verbose=verbose,
            )
            all_files.extend(files)

        # Remove any duplicates (in case of overlapping directories)
        all_files = sorted(set(all_files))

        if verbose:
            console.print(f"Found {len(all_files)} unique files")
            for f in all_files:
                console.print(f"  {f}")

        if not all_files:
            console.print("[yellow]No files found matching criteria[/]")
            raise typer.Exit(0)

        try:
            markdown = format_files(all_files, verbose=verbose)
        except Exception as e:
            console.print(f"[red]Error during formatting:[/] {str(e)}")
            raise typer.Exit(1)

        try:
            if outfile:
                outfile.write_text(markdown)
                console.print(f"Output written to [green]{outfile}[/]")
            else:
                pyperclip.copy(markdown)
                console.print(
                    f"[green]Copied[/] {len(all_files)} files to clipboard "
                    f"({len(markdown)} characters)"
                )
        except Exception as e:
            console.print(f"[red]Error during output:[/] {str(e)}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/] {str(e)}")
        raise typer.Exit(1)
