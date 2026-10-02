import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Final

import typer
from pydantic import ValidationError

from typesafe_unofficial_cli.auth.credentials import ApiKeyCredential
from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.providers import spec_for
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.output.columns import AUTH_STATUS
from typesafe_unofficial_cli.output.renderer import single
from typesafe_unofficial_cli.runtime.client_factory import ClientRequest
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode
from typesafe_unofficial_cli.runtime.params import options_from
from typesafe_unofficial_cli.services.validation import verify_key

if TYPE_CHECKING:
    from typesafe_unofficial_cli.auth.credentials import WritableCredentialStore
    from typesafe_unofficial_cli.auth.resolver import CredentialStores

APP: Final = typer.Typer(help="Log in, inspect, and remove API credentials.", no_args_is_help=True)


def _read_api_key(provider: Provider, *, with_token: bool) -> str:
    # No --api-key flag on purpose: a key passed as an argument ends up in shell history.
    raw = (
        sys.stdin.read()
        if with_token
        else typer.prompt(f"{spec_for(provider).display_name} API key", hide_input=True, err=True)
    )
    api_key = str(raw).strip()
    if not api_key:
        message = "The API key is empty."
        raise CliError(message, exit_code=ExitCode.USAGE)
    return api_key


def _select_store(stores: CredentialStores, *, insecure_storage: bool) -> WritableCredentialStore:
    if insecure_storage:
        return stores.file
    if stores.keyring.available():
        return stores.keyring
    message = "No system keyring backend is available."
    raise CliError(
        message,
        exit_code=ExitCode.CONFIGURATION,
        hint="Retry with --insecure-storage, or set the provider's API key variable in the environment.",
    )


def _status_record(profile_name: str, profile: Profile, source: str, masked_key: str) -> dict[str, object]:
    return {
        "profile": profile_name,
        "provider": profile.provider,
        "base_url": profile.effective_base_url(),
        "model": profile.model,
        "source": source,
        "api_key": masked_key,
    }


@dataclass(frozen=True, slots=True)
class _LoginOptions:
    provider: Annotated[
        Provider | None,
        typer.Option(
            "--provider",
            case_sensitive=False,
            help="Where the key is valid; defaults to the profile's, else typesafe.",
        ),
    ] = None
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Override the provider's API root, e.g. for a proxy."),
    ] = None
    with_token: Annotated[bool, typer.Option("--with-token", help="Read the API key from standard input.")] = False
    insecure_storage: Annotated[
        bool,
        typer.Option("--insecure-storage", help="Store the key in a 0600 plaintext file instead of the keyring."),
    ] = False
    skip_validation: Annotated[
        bool,
        typer.Option("--skip-validation", help="Store the key without calling the provider."),
    ] = False


@APP.command(
    help=(
        "Validate an API key and store it for the selected profile. "
        "A TypeSafe key is checked for free; an OpenRouter key needs one minimal billed request "
        "(skip it with --skip-validation). Environment variables for automation: "
        "TYPESAFE_API_KEY (provider typesafe) and OPENROUTER_API_KEY (provider openrouter)."
    ),
)
@handle_errors
@options_from(_LoginOptions)
def login(ctx: typer.Context, options: _LoginOptions) -> None:
    app_context = get_app_context(ctx)
    stores = app_context.services.credentials
    profile_name = app_context.options.profile_name
    current = app_context.options.profile
    resolved_provider = options.provider or current.provider
    # A different provider invalidates the old override and default model, which belong to the old host.
    keeps_settings = resolved_provider is current.provider
    try:
        profile = Profile(
            provider=resolved_provider,
            base_url=options.base_url or (current.base_url if keeps_settings else None),
            model=current.model if keeps_settings else None,
        )
    except ValidationError as error:
        message = error.errors()[0]["msg"].removeprefix("Value error, ")
        raise CliError(message, exit_code=ExitCode.USAGE) from error
    credential = ApiKeyCredential(api_key=_read_api_key(resolved_provider, with_token=options.with_token))
    if not options.skip_validation:
        request = ClientRequest(
            credential=credential,
            base_url=profile.effective_base_url(),
            model=profile.model,
            verbose=app_context.options.verbose,
        )
        with app_context.services.clients(request) as client:
            verify_key(client, resolved_provider)
    store = _select_store(stores, insecure_storage=options.insecure_storage)
    store.set(profile_name, credential)
    for other in stores.writable():
        if other is not store:
            other.delete(profile_name)
    settings = app_context.services.settings.load()
    if not settings.profiles:
        settings = settings.model_copy(update={"default_profile": profile_name})
    app_context.services.settings.save(settings.with_profile(profile_name, profile))
    app_context.notify(
        f"Logged in to profile '{profile_name}' ({spec_for(resolved_provider).display_name}, {store.source})."
    )
    app_context.render(single(_status_record(profile_name, profile, store.source, credential.masked()), AUTH_STATUS))


@APP.command(help="Show the active credential; --check also validates it with the provider.")
@handle_errors
def status(
    ctx: typer.Context,
    *,
    check: Annotated[
        bool, typer.Option("--check", help="Validate the key with the provider (OpenRouter bills one request).")
    ] = False,
) -> None:
    app_context = get_app_context(ctx)
    resolved = app_context.credential()
    if check:
        verify_key(app_context.client(), app_context.options.profile.provider)
    record = _status_record(
        app_context.options.profile_name,
        app_context.options.profile,
        resolved.source,
        resolved.credential.masked(),
    )
    app_context.render(single(record, AUTH_STATUS))


@APP.command(help="Remove the stored credential and profile.")
@handle_errors
def logout(ctx: typer.Context) -> None:
    app_context = get_app_context(ctx)
    services = app_context.services
    profile_name = app_context.options.profile_name
    removed = [store.source for store in services.credentials.writable() if store.delete(profile_name)]
    settings = services.settings.load()
    had_profile = profile_name in settings.profiles
    if had_profile:
        services.settings.save(settings.without_profile(profile_name))
    if not removed and not had_profile:
        message = f"No stored credentials for profile '{profile_name}'."
        raise CliError(message, exit_code=ExitCode.CONFIGURATION)
    app_context.notify(f"Logged out of profile '{profile_name}'.")
    provider = app_context.options.profile.provider
    if services.credentials.environment.get(profile_name, provider) is not None:
        variable = spec_for(provider).api_key_env_var
        app_context.notify(f"{variable} is still set in the environment and will keep being used.")


@APP.command(help="Print the raw API key of the active credential.")
@handle_errors
def token(ctx: typer.Context) -> None:
    resolved = get_app_context(ctx).credential()
    typer.echo(resolved.credential.api_key)
