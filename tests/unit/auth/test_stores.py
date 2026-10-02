from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from typesafe_unofficial_cli.auth.credentials import ApiKeyCredential
from typesafe_unofficial_cli.auth.credentials import CredentialSource
from typesafe_unofficial_cli.auth.credentials import decode
from typesafe_unofficial_cli.auth.credentials import encode
from typesafe_unofficial_cli.auth.env_store import EnvCredentialStore
from typesafe_unofficial_cli.auth.file_store import FileCredentialStore
from typesafe_unofficial_cli.auth.keyring_store import KeyringCredentialStore
from typesafe_unofficial_cli.auth.resolver import CredentialStores
from typesafe_unofficial_cli.config.providers import Provider

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import MemoryKeyring

CREDENTIAL: Final = ApiKeyCredential(api_key="abcdefgh1234")


def test_masked_shows_only_the_last_four_characters() -> None:
    # Arrange
    short = ApiKeyCredential(api_key="abc")
    # Act
    masked = (CREDENTIAL.masked(), short.masked())
    # Assert
    assert masked == ("********1234", "***")


def test_encode_decode_round_trip() -> None:
    # Arrange
    raw = encode(CREDENTIAL)
    # Act
    decoded = decode(raw)
    # Assert
    assert decoded == CREDENTIAL


def test_decode_rejects_garbage() -> None:
    # Arrange
    samples = ["not json", "[]", '{"kind": "oauth"}', '{"kind": "api_key", "api_key": ""}', '{"kind": "api_key"}']
    # Act
    decoded = [decode(sample) for sample in samples]
    # Assert
    assert decoded == [None] * len(samples)


def test_env_store_reads_each_providers_own_variable() -> None:
    # Arrange
    store = EnvCredentialStore({"TYPESAFE_API_KEY": " ts ", "OPENROUTER_API_KEY": "or"})
    # Act
    typesafe = store.get("any", Provider.TYPESAFE)
    openrouter = store.get("any", Provider.OPENROUTER)
    # Assert
    assert typesafe == ApiKeyCredential(api_key="ts")
    assert openrouter == ApiKeyCredential(api_key="or")


def test_env_store_ignores_blank_values() -> None:
    # Arrange
    store = EnvCredentialStore({"TYPESAFE_API_KEY": "  "})
    # Act
    credential = store.get("any", Provider.TYPESAFE)
    # Assert
    assert credential is None


def test_file_store_set_get_delete(tmp_path: Path) -> None:
    # Arrange
    store = FileCredentialStore(tmp_path / "credentials.toml")
    # Act
    store.set("work", CREDENTIAL)
    fetched = store.get("work", Provider.TYPESAFE)
    deleted = store.delete("work")
    missing = store.delete("work")
    # Assert
    assert (fetched, deleted, missing) == (CREDENTIAL, True, False)
    assert store.get("work", Provider.TYPESAFE) is None


def test_file_store_ignores_a_malformed_profiles_table(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "credentials.toml"
    path.write_text('profiles = "oops"\n', encoding="utf-8")
    # Act
    credential = FileCredentialStore(path).get("work", Provider.TYPESAFE)
    # Assert
    assert credential is None


def test_keyring_store_set_get_delete(memory_keyring: MemoryKeyring) -> None:
    # Arrange
    del memory_keyring
    store = KeyringCredentialStore()
    # Act
    store.set("work", CREDENTIAL)
    fetched = store.get("work", Provider.TYPESAFE)
    deleted = store.delete("work")
    missing = store.delete("work")
    # Assert
    assert (fetched, deleted, missing) == (CREDENTIAL, True, False)


def test_resolver_prefers_environment_over_keyring_over_file(tmp_path: Path, memory_keyring: MemoryKeyring) -> None:
    # Arrange
    del memory_keyring
    stores = CredentialStores(
        environment=EnvCredentialStore({"TYPESAFE_API_KEY": "from-env"}),
        keyring=KeyringCredentialStore(),
        file=FileCredentialStore(tmp_path / "credentials.toml"),
    )
    stores.keyring.set("p", ApiKeyCredential(api_key="from-keyring"))
    stores.file.set("p", ApiKeyCredential(api_key="from-file"))
    # Act
    first = stores.resolve("p", Provider.TYPESAFE)
    stores.environment._environ = {}  # ruff: ignore[private-member-access]
    second = stores.resolve("p", Provider.TYPESAFE)
    stores.keyring.delete("p")
    third = stores.resolve("p", Provider.TYPESAFE)
    # Assert
    assert first is not None
    assert [first.source, second.source if second else None, third.source if third else None] == [
        CredentialSource.ENVIRONMENT,
        CredentialSource.KEYRING,
        CredentialSource.FILE,
    ]
