from dataclasses import dataclass
from typing import Final

import typer
from typesafe_sdk import ListModelsResponse
from typesafe_sdk import TypeSafeError

from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.output.columns import MODELS
from typesafe_unofficial_cli.output.renderer import many
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode
from typesafe_unofficial_cli.runtime.params import options_from
from typesafe_unofficial_cli.runtime.request_options import RequestOptions

APP: Final = typer.Typer(help="Browse the System One models.", no_args_is_help=True)

_OPENROUTER_MODELS_URL: Final = "https://openrouter.ai/models?q=typesafe"


def _request_id(response: ListModelsResponse) -> str:
    try:
        return response.request_id
    except TypeSafeError:
        return "?"


@dataclass(frozen=True, slots=True)
class _ListOptions(RequestOptions):
    pass


@APP.command(name="list", help="List the models the account can use (TypeSafe provider only).")
@handle_errors
@options_from(_ListOptions)
def list_models(ctx: typer.Context, options: _ListOptions) -> None:
    app_context = get_app_context(ctx)
    if app_context.options.profile.provider is Provider.OPENROUTER:
        # OpenRouter answers /models in its own format, which the SDK rejects, so fail before any request.
        message = "`models list` is not available for an OpenRouter profile."
        raise CliError(
            message, exit_code=ExitCode.USAGE, hint=f"Browse the System One models at {_OPENROUTER_MODELS_URL}"
        )
    response = app_context.client(options.overrides()).models.list()
    if app_context.options.verbose:
        app_context.notify(f"request id: {_request_id(response)}")
    app_context.render(many(response.models, MODELS, id_key="name"))
