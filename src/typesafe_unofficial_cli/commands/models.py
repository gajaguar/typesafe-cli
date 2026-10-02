from typing import Final

import typer

from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.output.columns import MODELS
from typesafe_unofficial_cli.output.renderer import many
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

APP: Final = typer.Typer(help="Browse the System One models.", no_args_is_help=True)

_OPENROUTER_MODELS_URL: Final = "https://openrouter.ai/models?q=typesafe"


@APP.command(name="list", help="List the models the account can use (TypeSafe provider only).")
@handle_errors
def list_models(ctx: typer.Context) -> None:
    app_context = get_app_context(ctx)
    if app_context.options.profile.provider is Provider.OPENROUTER:
        # OpenRouter answers /models in its own format, which the SDK rejects, so fail before any request.
        message = "`models list` is not available for an OpenRouter profile."
        raise CliError(
            message, exit_code=ExitCode.USAGE, hint=f"Browse the System One models at {_OPENROUTER_MODELS_URL}"
        )
    models = app_context.client().models.list().models
    app_context.render(many(models, MODELS, id_key="name"))
