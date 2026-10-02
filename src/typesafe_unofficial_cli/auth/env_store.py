from __future__ import annotations

from typing import TYPE_CHECKING

from typesafe_unofficial_cli.auth.credentials import ApiKeyCredential
from typesafe_unofficial_cli.auth.credentials import CredentialSource
from typesafe_unofficial_cli.config.providers import spec_for

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typesafe_unofficial_cli.config.providers import Provider


# The environment key is profile-agnostic: it overrides whatever profile is selected, for CI. It is
# looked up by the profile's provider, so each host only ever receives its own key.
class EnvCredentialStore:
    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environ = environ

    @property
    def source(self) -> CredentialSource:
        return CredentialSource.ENVIRONMENT

    def get(self, profile: str, provider: Provider) -> ApiKeyCredential | None:
        del profile
        api_key = self._environ.get(spec_for(provider).api_key_env_var, "").strip()
        return ApiKeyCredential(api_key=api_key) if api_key else None
