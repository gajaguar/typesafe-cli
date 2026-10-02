from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Final

import httpx2
import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError
from typer.testing import CliRunner
from typesafe_sdk import AsyncTypeSafeClient
from typesafe_sdk import RetryPolicy
from typesafe_sdk import TypeSafeClient

from typesafe_unofficial_cli.auth.env_store import EnvCredentialStore
from typesafe_unofficial_cli.auth.file_store import FileCredentialStore
from typesafe_unofficial_cli.auth.keyring_store import KeyringCredentialStore
from typesafe_unofficial_cli.auth.resolver import CredentialStores
from typesafe_unofficial_cli.config.store import SettingsStore
from typesafe_unofficial_cli.main import create_app
from typesafe_unofficial_cli.runtime.context import Services

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from pathlib import Path

    import typer

    from typesafe_unofficial_cli.runtime.client_factory import ClientRequest

MODELS_PAYLOAD: Final = {
    "models": [
        {"name": "jev-1.13", "description": "Structured decisions.", "release_date": "2026-09-17"},
        {"name": "jev-1.12", "description": "Previous release.", "release_date": "2026-08-01"},
    ],
}

SYSTEM_ONE_PAYLOAD: Final = {
    "model": "jev-1.13",
    "answers": {
        "billing": {"type": "noul", "noul": 0.93},
        "tone": {
            "type": "choice",
            "choice": "angry",
            "confidence": 0.8,
            "probabilities": {"calm": 0.1, "angry": 0.9},
        },
        "urgency": {
            "type": "score",
            "score": 2.4,
            "confidence": 0.7,
            "legend": {"0": "low", "1": "medium", "2": "high"},
            "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7},
        },
    },
    "usage": {"input_tokens": 12, "output_tokens": 3},
}

QUESTIONS: Final = {
    "billing": {"type": "noul", "instructions": "Is this about billing?"},
    "tone": {"type": "choice", "instructions": "What is the tone?", "criteria": {"calm": None, "angry": None}},
    "urgency": {"type": "score", "instructions": "How urgent is it?", "criteria": ["low", "medium", "high"]},
}


class MemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        super().__init__()
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.passwords[service, username] = password

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) not in self.passwords:
            raise PasswordDeleteError(username)
        del self.passwords[service, username]


# Stands in for the provider's HTTP API: every request is recorded and answered by `handler`.
@dataclass(slots=True)
class FakeApi:
    handler: Callable[[httpx2.Request], httpx2.Response] = field(
        default=lambda request: httpx2.Response(404, json={"detail": f"no route for {request.url}"}),
    )
    requests: list[httpx2.Request] = field(default_factory=list)

    def respond(self, status: int, payload: object) -> None:
        self.handler = lambda _request: httpx2.Response(status, json=payload)

    def serve(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.handler(request)

    def bodies(self) -> list[dict[str, object]]:
        return [json.loads(request.content) for request in self.requests if request.content]


@pytest.fixture(name="api")
def api_fixture() -> FakeApi:
    return FakeApi()


@pytest.fixture(name="memory_keyring")
def memory_keyring_fixture() -> Iterator[MemoryKeyring]:
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture(name="environ")
def environ_fixture() -> dict[str, str]:
    return {}


@pytest.fixture(name="services")
def services_fixture(tmp_path: Path, memory_keyring: MemoryKeyring, environ: dict[str, str], api: FakeApi) -> Services:
    del memory_keyring

    def fake_client(request: ClientRequest) -> TypeSafeClient:
        return TypeSafeClient(
            api_key=request.credential.api_key,
            base_url=request.base_url,
            model=request.model,
            retry=RetryPolicy(max_retries=0),
            headers=request.headers,
            transport=httpx2.MockTransport(api.serve),
        )

    def fake_async_client(request: ClientRequest) -> AsyncTypeSafeClient:
        return AsyncTypeSafeClient(
            api_key=request.credential.api_key,
            base_url=request.base_url,
            model=request.model,
            retry=RetryPolicy(max_retries=0),
            headers=request.headers,
            transport=httpx2.MockTransport(api.serve),
        )

    return Services(
        settings=SettingsStore(tmp_path / "config.toml"),
        credentials=CredentialStores(
            environment=EnvCredentialStore(environ),
            keyring=KeyringCredentialStore(),
            file=FileCredentialStore(tmp_path / "credentials.toml"),
        ),
        clients=fake_client,
        async_clients=fake_async_client,
    )


@pytest.fixture
def cli(services: Services) -> typer.Typer:
    return create_app(lambda: services)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
