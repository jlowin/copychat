import typer

from collections.abc import Callable, Sequence
from typing import Any

import click
from typer.core import DEFAULT_MARKUP_MODE, MarkupMode
from typer.models import CommandFunctionType


class TyperDefaultCommand(typer.core.TyperCommand):
    """Type that indicates if a command is the default command."""


class TyperGroupWithDefault(typer.core.TyperGroup):
    """Use a default command if specified."""

    def __init__(
        self,
        *,
        name: str | None = None,
        commands: dict[str, click.Command] | Sequence[click.Command] | None = None,
        rich_markup_mode: MarkupMode = DEFAULT_MARKUP_MODE,
        rich_help_panel: str | None = None,
        **attrs: Any,
    ) -> None:
        super().__init__(
            name=name,
            commands=commands,
            rich_markup_mode=rich_markup_mode,
            rich_help_panel=rich_help_panel,
            **attrs,
        )
        # find the default command if any
        self.default_command = None
        if len(self.commands) > 1:
            for name, command in reversed(self.commands.items()):
                if isinstance(command, TyperDefaultCommand):
                    self.default_command = name
                    break

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        # if --help is specified, show the group help
        # else if default command was specified in the group and no args or no subcommand is specified, use the default command
        if (
            self.default_command
            and (not args or args[0] not in self.commands)
            and "--help" not in args
        ):
            args = [self.default_command] + args
        return super().make_context(info_name, args, parent, **extra)


class TyperWithDefaultCommand(typer.Typer):
    """A Typer class with default command support.
    https://github.com/fastapi/typer/issues/18

    @app.command(default=True)
    def default_command():
       '''This is the default command.'''
        pass

    @app.command()
    def some_command():
        pass

    """

    def __init__(self, **kwargs):
        super().__init__(cls=TyperGroupWithDefault, **kwargs)

    def command(
        self, default: bool = False, **kwargs
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        return super().command(cls=TyperDefaultCommand if default else None, **kwargs)
