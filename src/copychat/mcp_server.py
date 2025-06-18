from typing import Annotated
from fastmcp import FastMCP
from pydantic import Field
import pyperclip

from typer.testing import CliRunner

mcp = FastMCP(
    "Copychat",
    instructions="An MCP server for copying source code and GitHub items to the clipboard. Use this whenever the user wants you to copy something.",
)


@mcp.tool
def copy_text_to_clipboard(text: str) -> None:
    """Copy any text to the clipboard. This is useful for copying ad-hoc text.
    For files, use `copychat_files` instead."""
    pyperclip.copy(text)
    return f"Copied {len(text)} characters to the clipboard."


@mcp.tool
def read_clipboard() -> str:
    """Read the clipboard."""
    return pyperclip.paste()


@mcp.tool
def copy_files_to_clipboard(
    paths: list[str],
    include: Annotated[
        str | None,
        Field(
            description="Comma-separated list of file extensions to include, e.g. 'py,js,ts'. If None (default), all files are included."
        ),
    ] = None,
    exclude: Annotated[
        str | None,
        Field(
            description="Comma-separated list of glob patterns to exclude, e.g. '*.pyc,*.pyo,*.pyd'. If None (default), no files are excluded."
        ),
    ] = None,
    append_to_clipboard: Annotated[
        bool,
        Field(
            description="If True, appends to the existing clipboard. If False (default), overwrites the clipboard."
        ),
    ] = False,
) -> None:
    """Copy local files to the clipboard without loading them into context."""
    from copychat.cli import app

    if not paths:
        raise ValueError("No paths provided")

    runner = CliRunner()

    args = [*paths]

    if include:
        args.append("--include")
        args.append(include)

    if exclude:
        args.append("--exclude")
        args.append(exclude)

    if append_to_clipboard:
        args.append("--append")

    result = runner.invoke(app, args + ["-v"])

    if result.exception:
        raise result.exception

    return result.output


if __name__ == "__main__":
    mcp.run()
