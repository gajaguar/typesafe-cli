from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Final

import typer
from rich.console import Console

from typesafe_unofficial_cli._version import __version__
from typesafe_unofficial_cli.auth.env_store import EnvCredentialStore
from typesafe_unofficial_cli.auth.file_store import FileCredentialStore
from typesafe_unofficial_cli.auth.keyring_store import KeyringCredentialStore
from typesafe_unofficial_cli.auth.resolver import CredentialStores
from typesafe_unofficial_cli.commands import ask
from typesafe_unofficial_cli.commands import auth
from typesafe_unofficial_cli.commands import config
from typesafe_unofficial_cli.commands import models
from typesafe_unofficial_cli.config.paths import credentials_file
from typesafe_unofficial_cli.config.paths import settings_file
from typesafe_unofficial_cli.config.settings import GlobalOptions
from typesafe_unofficial_cli.config.settings import OutputFormat
from typesafe_unofficial_cli.config.settings import resolve_options
from typesafe_unofficial_cli.config.store import SettingsStore
from typesafe_unofficial_cli.output.registry import create_renderer
from typesafe_unofficial_cli.output.renderer import RenderTarget
from typesafe_unofficial_cli.runtime.client_factory import create_async_sdk_client
from typesafe_unofficial_cli.runtime.client_factory import create_sdk_client
from typesafe_unofficial_cli.runtime.context import AppContext
from typesafe_unofficial_cli.runtime.context import Services
from typesafe_unofficial_cli.runtime.errors import handle_errors

if TYPE_CHECKING:
    from collections.abc import Callable


def default_services() -> Services:
    return Services(
        settings=SettingsStore(settings_file()),
        credentials=CredentialStores(
            environment=EnvCredentialStore(os.environ),
            keyring=KeyringCredentialStore(),
            file=FileCredentialStore(credentials_file()),
        ),
        clients=create_sdk_client,
        async_clients=create_async_sdk_client,
    )


def print_version(
    value: bool,  # ruff: ignore[boolean-type-hint-positional-argument]  Typer passes the flag value positionally
) -> None:
    if value:
        typer.echo(f"typesafe {__version__}")
        raise typer.Exit


# Global options must precede the sub-command (`typesafe -o json auth status`). Colors follow
# Rich's NO_COLOR handling, so there is no --no-color flag to keep the callback small.
def create_app(services_factory: Callable[[], Services] = default_services) -> typer.Typer:
    cli = typer.Typer(
        name="typesafe",
        help="Unofficial command-line interface for TypeSafe AI System One models, on TypeSafe or OpenRouter.",
        no_args_is_help=True,
    )

    @cli.callback()
    @handle_errors
    def root(
        ctx: typer.Context,
        *,
        profile: Annotated[
            str | None,
            typer.Option("--profile", "-p", envvar="TYPESAFE_CLI_PROFILE", help="Configuration profile to use."),
        ] = None,
        output: Annotated[
            OutputFormat | None,
            typer.Option("--output", "-o", envvar="TYPESAFE_CLI_OUTPUT", case_sensitive=False, help="Output format."),
        ] = None,
        verbose: Annotated[
            bool,
            typer.Option("--verbose", "-v", help="Log the SDK's HTTP activity to stderr."),
        ] = False,
        version: Annotated[
            bool,
            typer.Option("--version", callback=print_version, is_eager=True, help="Show the version and exit."),
        ] = False,
    ) -> None:
        del version
        flags = GlobalOptions(profile=profile, output=output, verbose=verbose)
        _bind_context(ctx=ctx, services=services_factory(), flags=flags)

    def _bind_context(*, ctx: typer.Context, services: Services, flags: GlobalOptions) -> None:
        resolved = resolve_options(flags, services.settings.load(), is_tty=sys.stdout.isatty())
        console = Console(highlight=False)
        renderer = create_renderer(resolved.output, RenderTarget(console=console, stream=sys.stdout))
        app_context = AppContext(options=resolved, services=services, console=console, renderer=renderer)
        ctx.obj = app_context
        ctx.call_on_close(app_context.close)

    cli.add_typer(auth.APP, name="auth")
    cli.add_typer(config.APP, name="config")
    cli.add_typer(models.APP, name="models")
    cli.registered_commands.extend(ask.APP.registered_commands)
    return cli


APP: Final = create_app()


def run() -> None:
    APP(prog_name="typesafe")
