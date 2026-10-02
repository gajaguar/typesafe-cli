from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from typing import Final
from typing import Literal
from typing import Protocol

if TYPE_CHECKING:
    from typesafe_unofficial_cli.config.providers import Provider

_VISIBLE_SUFFIX: Final = 4


class CredentialSource(StrEnum):
    ENVIRONMENT = "environment"
    KEYRING = "keyring"
    FILE = "file"


# Both providers authenticate with a bearer API key. The tagged encoding leaves room for another
# credential kind without migrating what is already stored.
@dataclass(frozen=True, slots=True)
class ApiKeyCredential:
    api_key: str
    kind: Literal["api_key"] = "api_key"

    def masked(self) -> str:
        if len(self.api_key) <= _VISIBLE_SUFFIX:
            return "*" * len(self.api_key)
        return "*" * 8 + self.api_key[-_VISIBLE_SUFFIX:]


type Credential = ApiKeyCredential  # pylint: disable=gajaguar-module-const-naming


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    credential: Credential
    source: CredentialSource


def encode(credential: Credential) -> str:
    return json.dumps({"kind": credential.kind, "api_key": credential.api_key})


def decode(raw: str) -> Credential | None:
    try:
        payload: object = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get("kind") != "api_key":
        return None
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or not api_key:
        return None
    return ApiKeyCredential(api_key=api_key)


# `provider` only matters to the environment store, which reads a different variable per provider.
class CredentialStore(Protocol):
    @property
    def source(self) -> CredentialSource: ...

    def get(self, profile: str, provider: Provider) -> Credential | None: ...


class WritableCredentialStore(CredentialStore, Protocol):
    def available(self) -> bool: ...

    def set(self, profile: str, credential: Credential) -> None: ...

    def delete(self, profile: str) -> bool: ...
