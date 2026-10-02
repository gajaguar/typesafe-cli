from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

    from typesafe_unofficial_cli.runtime.context import Services


def test_config_path_prints_settings_file(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    args = ["config", "path"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert result.stdout.strip() == str(services.settings.path)


def test_config_list_shows_effective_base_url(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(
        Settings(
            default_profile="or",
            profiles={"work": Profile(), "or": Profile(provider=Provider.OPENROUTER, model="jev-1.13")},
        ),
    )
    # Act
    result = runner.invoke(cli, ["config", "list"])
    # Assert
    assert result.exit_code == ExitCode.OK
    rows = json.loads(result.stdout)
    assert {row["name"]: (row["default"], row["base_url"]) for row in rows} == {
        "or": (True, "https://openrouter.ai/api"),
        "work": (False, "https://api.typesafe.ai"),
    }


def test_config_list_id_format_prints_profile_names(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(Settings(profiles={"a": Profile(), "b": Profile()}))
    # Act
    result = runner.invoke(cli, ["-o", "id", "config", "list"])
    # Assert
    assert result.stdout.split() == ["a", "b"]


def test_config_use_sets_default_profile(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(Settings(profiles={"a": Profile(), "b": Profile()}))
    # Act
    result = runner.invoke(cli, ["config", "use", "b"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert services.settings.load().default_profile == "b"


def test_config_use_unknown_profile_exits_configuration(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["config", "use", "missing"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION
