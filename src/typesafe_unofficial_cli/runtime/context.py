from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from rich.console import Console

from typesafe_unofficial_cli.runtime.client_factory import ClientRequest
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    import typer
    from typesafe_sdk import AsyncTypeSafeClient
    from typesafe_sdk import TypeSafeClient

    from typesafe_unofficial_cli.auth.credentials import ResolvedCredential
    from typesafe_unofficial_cli.auth.resolver import CredentialStores
    from typesafe_unofficial_cli.config.settings import ResolvedOptions
    from typesafe_unofficial_cli.config.store import SettingsStore
    from typesafe_unofficial_cli.output.renderer import Dataset
    from typesafe_unofficial_cli.output.renderer import Renderer
    from typesafe_unofficial_cli.runtime.client_factory import AsyncClientFactory
    from typesafe_unofficial_cli.runtime.client_factory import ClientFactory
    from typesafe_unofficial_cli.runtime.request_options import RequestOverrides


@dataclass(frozen=True, slots=True)
class Services:
    settings: SettingsStore
    credentials: CredentialStores
    clients: ClientFactory
    async_clients: AsyncClientFactory


# Built once per invocation by the root callback and shared with every command through
# typer.Context.obj; the SDK client is created lazily so offline commands never need a key.
@dataclass(slots=True)
class AppContext:
    options: ResolvedOptions
    services: Services
    console: Console
    renderer: Renderer
    _client: TypeSafeClient | None = field(default=None, init=False, repr=False)

    def credential(self) -> ResolvedCredential:
        profile = self.options.profile
        resolved = self.services.credentials.resolve(self.options.profile_name, profile.provider)
        if resolved is None:
            message = f"Not logged in (profile '{self.options.profile_name}')."
            hint = (
                "Run `typesafe auth login`, or set the provider's API key variable (see `typesafe auth login --help`)."
            )
            raise CliError(message, exit_code=ExitCode.CONFIGURATION, hint=hint)
        return resolved

    # Flag overrides win over the profile; the SDK applies its own defaults to what neither sets.
    def client_request(self, overrides: RequestOverrides | None = None) -> ClientRequest:
        profile = self.options.profile
        return ClientRequest(
            credential=self.credential().credential,
            base_url=profile.effective_base_url(),
            model=profile.model,
            verbose=self.options.verbose,
            timeout=overrides.timeout if overrides and overrides.timeout is not None else profile.timeout,
            max_retries=(
                overrides.max_retries if overrides and overrides.max_retries is not None else profile.max_retries
            ),
            headers=overrides.headers if overrides else None,
        )

    def client(self, overrides: RequestOverrides | None = None) -> TypeSafeClient:
        if self._client is None:
            self._client = self.services.clients(self.client_request(overrides))
        return self._client

    def async_client(self, overrides: RequestOverrides | None = None) -> AsyncTypeSafeClient:
        return self.services.async_clients(self.client_request(overrides))

    # Status messages go to stderr so stdout stays clean for piping rendered data.
    @staticmethod
    def notify(message: str) -> None:
        Console(stderr=True, highlight=False).print(message, markup=False)

    def render(self, dataset: Dataset) -> None:
        self.renderer.render(dataset)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


def get_app_context(ctx: typer.Context) -> AppContext:
    obj: object = ctx.find_root().obj
    if not isinstance(obj, AppContext):
        message = "CLI context is not initialized."
        raise CliError(message)
    return obj
