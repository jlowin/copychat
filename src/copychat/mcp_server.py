from typing import Annotated
from fastmcp import FastMCP
from pydantic import Field
import pyperclip

mcp = FastMCP(
    "Copychat",
    instructions="An MC server for copying source code and GitHub items to the clipboard.",
)


@mcp.tool
def copy_to_clipboard(text: str) -> None:
    """Copy any text to the clipboard."""
    pyperclip.copy(text)
    return f"Copied {len(text)} characters to the clipboard."


@mcp.tool
def read_clipboard() -> str:
    """Read the clipboard."""
    return pyperclip.paste()


@mcp.tool
def copychat_files(
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
    """Copy local files to the clipboard."""
    from copychat.cli import main

    main(
        paths=paths,
        include=include,
        exclude=exclude.split(",") if exclude else None,
        append=append_to_clipboard,
        quiet=True,
    )
    return "Copied files to the clipboard."


if __name__ == "__main__":
    mcp.run()
