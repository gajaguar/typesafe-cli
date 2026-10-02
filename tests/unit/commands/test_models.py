from __future__ import annotations

import json
from typing import TYPE_CHECKING

from tests.conftest import MODELS_PAYLOAD
from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

    from tests.conftest import FakeApi
    from typesafe_unofficial_cli.runtime.context import Services


def test_models_list_json_keeps_api_field_names(
    runner: CliRunner, cli: typer.Typer, environ: dict[str, str], api: FakeApi
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    expected = MODELS_PAYLOAD["models"]
    api.respond(200, MODELS_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["-o", "json", "models", "list"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert json.loads(result.stdout) == expected


def test_models_list_id_format_prints_names(
    runner: CliRunner, cli: typer.Typer, environ: dict[str, str], api: FakeApi
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    api.respond(200, MODELS_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["-o", "id", "models", "list"])
    # Assert
    assert result.stdout.split() == ["jev-1.13", "jev-1.12"]


def test_models_list_csv_has_header_and_rows(
    runner: CliRunner, cli: typer.Typer, environ: dict[str, str], api: FakeApi
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    api.respond(200, MODELS_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["-o", "csv", "models", "list"])
    # Assert
    header, first, *_ = result.stdout.splitlines()
    assert (header, first) == ("Name,Released,Description", "jev-1.13,2026-09-17,Structured decisions.")


def test_models_list_for_openrouter_exits_usage_without_a_request(
    runner: CliRunner, cli: typer.Typer, services: Services, environ: dict[str, str], api: FakeApi
) -> None:
    # Arrange
    environ["OPENROUTER_API_KEY"] = "secret"
    services.settings.save(Settings(profiles={"default": Profile(provider=Provider.OPENROUTER)}))
    # Act
    result = runner.invoke(cli, ["models", "list"])
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert "openrouter.ai/models" in result.stderr
    assert api.requests == []


def test_models_list_without_login_exits_configuration(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["models", "list"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION
