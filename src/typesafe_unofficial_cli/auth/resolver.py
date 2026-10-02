from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from typesafe_unofficial_cli.auth.credentials import ResolvedCredential

if TYPE_CHECKING:
    from typesafe_unofficial_cli.auth.credentials import CredentialStore
    from typesafe_unofficial_cli.auth.credentials import WritableCredentialStore
    from typesafe_unofficial_cli.auth.env_store import EnvCredentialStore
    from typesafe_unofficial_cli.auth.file_store import FileCredentialStore
    from typesafe_unofficial_cli.auth.keyring_store import KeyringCredentialStore
    from typesafe_unofficial_cli.config.providers import Provider


@dataclass(frozen=True, slots=True)
class CredentialStores:
    environment: EnvCredentialStore
    keyring: KeyringCredentialStore
    file: FileCredentialStore

    # Precedence order: the first store holding a credential for the profile wins.
    def chain(self) -> tuple[CredentialStore, ...]:
        return (self.environment, self.keyring, self.file)

    def writable(self) -> tuple[WritableCredentialStore, ...]:
        return (self.keyring, self.file)

    def resolve(self, profile: str, provider: Provider) -> ResolvedCredential | None:
        for store in self.chain():
            credential = store.get(profile, provider)
            if credential is not None:
                return ResolvedCredential(credential=credential, source=store.source)
        return None
