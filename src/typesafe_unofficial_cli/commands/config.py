from typing import TYPE_CHECKING
from typing import Annotated
from typing import Final

import typer
from pydantic import ValidationError

from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.output.columns import PROFILES
from typesafe_unofficial_cli.output.renderer import Dataset
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from typesafe_unofficial_cli.runtime.context import AppContext

_PROFILE_KEYS: Final = ("provider", "base_url", "model", "timeout", "max_retries")
_GLOBAL_KEYS: Final = ("output",)
_KEYS_HINT: Final = f"Valid keys: {', '.join((*_PROFILE_KEYS, *_GLOBAL_KEYS))}."

APP: Final = typer.Typer(help="Inspect and edit local CLI configuration.", no_args_is_help=True)


@APP.command(help="Print the settings file location.")
@handle_errors
def path(ctx: typer.Context) -> None:
    typer.echo(str(get_app_context(ctx).services.settings.path))


@APP.command(name="list", help="List configured profiles.")
@handle_errors
def list_profiles(ctx: typer.Context) -> None:
    app_context = get_app_context(ctx)
    settings = app_context.services.settings.load()
    records = [
        {
            "name": name,
            "default": name == settings.default_profile,
            "provider": profile.provider,
            "base_url": profile.effective_base_url(),
            "model": profile.model,
        }
        for name, profile in sorted(settings.profiles.items())
    ]
    app_context.render(Dataset(records=records, columns=PROFILES, id_key="name"))


@APP.command(help="Set the default profile.")
@handle_errors
def use(ctx: typer.Context, name: Annotated[str, typer.Argument(help="Name of an existing profile.")]) -> None:
    app_context = get_app_context(ctx)
    store = app_context.services.settings
    settings = store.load()
    if name not in settings.profiles:
        message = f"Unknown profile '{name}'."
        raise CliError(message, exit_code=ExitCode.CONFIGURATION, hint="Run `typesafe config list`.")
    store.save(settings.model_copy(update={"default_profile": name}))
    app_context.notify(f"Default profile set to '{name}'.")


def _check_key(key: str) -> None:
    if key not in {*_PROFILE_KEYS, *_GLOBAL_KEYS}:
        message = f"Unknown key '{key}'."
        raise CliError(message, exit_code=ExitCode.USAGE, hint=_KEYS_HINT)


def _validation_message(error: ValidationError) -> str:
    return error.errors()[0]["msg"].removeprefix("Value error, ")


def _profile_fields(current: Profile, key: str, value: str | None) -> dict[str, object]:
    fields: dict[str, object] = current.model_dump()
    if value is None:
        fields.pop(key)
        return fields
    if key == "provider" and value != current.provider:
        fields.update(base_url=None, model=None)
    fields[key] = value
    return fields


# `value=None` unsets the key. A new provider drops base_url and model, which belong to the old host
# (the same rule `auth login` applies).
def _updated(settings: Settings, profile_name: str, key: str, value: str | None) -> Settings:
    try:
        if key == "output":
            return Settings.model_validate({**settings.model_dump(), "output": value})
        fields = _profile_fields(settings.profiles.get(profile_name, Profile()), key, value)
        return settings.with_profile(profile_name, Profile.model_validate(fields))
    except ValidationError as error:
        raise CliError(_validation_message(error), exit_code=ExitCode.USAGE) from error


def _current_value(app_context: AppContext, key: str) -> object:
    if key == "output":
        output = app_context.services.settings.load().output
        return None if output is None else output.value
    return getattr(app_context.options.profile, key)


@APP.command(name="set", help="Set a profile key (provider, base_url, model, timeout, max_retries) or `output`.")
@handle_errors
def set_value(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting to change.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    _check_key(key)
    app_context = get_app_context(ctx)
    store = app_context.services.settings
    store.save(_updated(store.load(), app_context.options.profile_name, key, value))
    app_context.notify(f"Set {key} for profile '{app_context.options.profile_name}'.")


@APP.command(help="Remove a setting so the default applies again.")
@handle_errors
def unset(ctx: typer.Context, key: Annotated[str, typer.Argument(help="Setting to clear.")]) -> None:
    _check_key(key)
    app_context = get_app_context(ctx)
    store = app_context.services.settings
    store.save(_updated(store.load(), app_context.options.profile_name, key, None))
    app_context.notify(f"Cleared {key} for profile '{app_context.options.profile_name}'.")


@APP.command(help="Print the value of a setting; nothing is printed when it is unset.")
@handle_errors
def get(ctx: typer.Context, key: Annotated[str, typer.Argument(help="Setting to read.")]) -> None:
    _check_key(key)
    value = _current_value(get_app_context(ctx), key)
    if value is not None:
        typer.echo(str(value))
