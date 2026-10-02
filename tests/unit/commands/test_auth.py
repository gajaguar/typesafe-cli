from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Final

from tests.conftest import MODELS_PAYLOAD
from tests.conftest import SYSTEM_ONE_PAYLOAD
from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

    from tests.conftest import FakeApi
    from tests.conftest import MemoryKeyring
    from typesafe_unofficial_cli.runtime.context import Services

KEY: Final = "ts-secret-key-1234"


def test_login_typesafe_validates_with_models_and_stores_key(
    runner: CliRunner, cli: typer.Typer, services: Services, api: FakeApi, memory_keyring: MemoryKeyring
) -> None:
    # Arrange
    api.respond(200, MODELS_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["-o", "json", "auth", "login", "--with-token"], input=f"{KEY}\n")
    # Assert
    assert result.exit_code == ExitCode.OK
    assert [(request.method, request.url.path) for request in api.requests] == [("GET", "/v1/models")]
    assert api.requests[0].url.host == "api.typesafe.ai"
    assert api.requests[0].headers["authorization"] == f"Bearer {KEY}"
    payload = json.loads(result.stdout)
    shown = {key: payload[key] for key in ("provider", "api_key")}
    assert shown == {"provider": "typesafe", "api_key": "********1234"}
    assert KEY not in result.stdout
    assert ("typesafe-cli", "default") in memory_keyring.passwords
    assert services.settings.load().profiles == {"default": Profile()}


def test_login_openrouter_probes_system_one_on_openrouter_host(
    runner: CliRunner, cli: typer.Typer, services: Services, api: FakeApi
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["-p", "or", "auth", "login", "--provider", "openrouter", "--with-token"], input=KEY)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert [(request.method, str(request.url)) for request in api.requests] == [
        ("POST", "https://openrouter.ai/api/v1/systemone"),
    ]
    assert services.settings.load().profiles["or"].provider is Provider.OPENROUTER


def test_login_with_rejected_key_stores_nothing(
    runner: CliRunner, cli: typer.Typer, services: Services, api: FakeApi, memory_keyring: MemoryKeyring
) -> None:
    # Arrange
    api.respond(401, {"detail": "Missing or invalid API key"})
    # Act
    result = runner.invoke(cli, ["auth", "login", "--with-token"], input=KEY)
    # Assert
    assert result.exit_code == ExitCode.AUTHENTICATION
    assert "typesafe auth login" in result.stderr
    assert memory_keyring.passwords == {}
    assert services.settings.load() == Settings()


def test_login_skip_validation_makes_no_request(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, memory_keyring: MemoryKeyring
) -> None:
    # Arrange
    args = ["auth", "login", "--with-token", "--skip-validation"]
    # Act
    result = runner.invoke(cli, args, input=KEY)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.requests == []
    assert ("typesafe-cli", "default") in memory_keyring.passwords


def test_login_with_empty_key_exits_usage(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["auth", "login", "--with-token"]
    # Act
    result = runner.invoke(cli, args, input="  \n")
    # Assert
    assert result.exit_code == ExitCode.USAGE


def test_login_insecure_storage_writes_owner_only_file(
    runner: CliRunner, cli: typer.Typer, services: Services, memory_keyring: MemoryKeyring
) -> None:
    # Arrange
    args = ["auth", "login", "--with-token", "--skip-validation", "--insecure-storage"]
    # Act
    result = runner.invoke(cli, args, input=KEY)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert services.credentials.file.path.stat().st_mode & 0o777 == 0o600
    assert memory_keyring.passwords == {}


def test_login_base_url_must_be_https(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    args = ["auth", "login", "--with-token", "--skip-validation", "--base-url", "http://example.com"]
    # Act
    result = runner.invoke(cli, args, input=KEY)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert "base_url must be an https URL" in result.stderr
    assert services.settings.load().profiles == {}


def test_switching_provider_drops_the_old_host_overrides(
    runner: CliRunner, cli: typer.Typer, services: Services
) -> None:
    # Arrange
    services.settings.save(
        Settings(profiles={"default": Profile(base_url="https://proxy.example.com", model="jev-1.12")}),
    )
    args = ["auth", "login", "--provider", "openrouter", "--with-token", "--skip-validation"]
    # Act
    result = runner.invoke(cli, args, input=KEY)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert services.settings.load().profiles["default"] == Profile(provider=Provider.OPENROUTER)


def test_status_shows_masked_key_and_source(runner: CliRunner, cli: typer.Typer, environ: dict[str, str]) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = KEY
    # Act
    result = runner.invoke(cli, ["-o", "json", "auth", "status"])
    # Assert
    assert result.exit_code == ExitCode.OK
    payload = json.loads(result.stdout)
    assert {key: payload[key] for key in ("source", "base_url")} == {
        "source": "environment",
        "base_url": "https://api.typesafe.ai",
    }
    assert KEY not in result.stdout


def test_status_check_verifies_the_key_with_the_provider(
    runner: CliRunner, cli: typer.Typer, environ: dict[str, str], api: FakeApi
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = KEY
    api.respond(200, MODELS_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["auth", "status", "--check"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert len(api.requests) == 1


def test_status_without_credentials_exits_configuration(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["auth", "status"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION
    assert "Not logged in" in result.stderr


def test_environment_key_is_per_provider(
    runner: CliRunner, cli: typer.Typer, services: Services, environ: dict[str, str]
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = KEY
    services.settings.save(Settings(profiles={"default": Profile(provider=Provider.OPENROUTER)}))
    # Act
    result = runner.invoke(cli, ["auth", "status"])
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION


def test_logout_removes_key_and_profile(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    runner.invoke(cli, ["auth", "login", "--with-token", "--skip-validation"], input=KEY)
    # Act
    result = runner.invoke(cli, ["auth", "logout"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert services.credentials.resolve("default", Provider.TYPESAFE) is None
    assert services.settings.load().profiles == {}


def test_logout_warns_when_environment_key_remains(
    runner: CliRunner, cli: typer.Typer, environ: dict[str, str]
) -> None:
    # Arrange
    runner.invoke(cli, ["auth", "login", "--with-token", "--skip-validation"], input=KEY)
    environ["TYPESAFE_API_KEY"] = KEY
    # Act
    result = runner.invoke(cli, ["auth", "logout"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert "TYPESAFE_API_KEY is still set" in result.stderr


def test_logout_without_anything_stored_exits_configuration(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["auth", "logout"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION


def test_token_prints_the_raw_key(runner: CliRunner, cli: typer.Typer, environ: dict[str, str]) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = KEY
    # Act
    result = runner.invoke(cli, ["auth", "token"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert result.stdout == f"{KEY}\n"
