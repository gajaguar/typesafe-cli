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


def test_config_set_and_get_a_profile_value(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    set_args = ["config", "set", "model", "jev-1.13"]
    # Act
    set_result = runner.invoke(cli, set_args)
    get_result = runner.invoke(cli, ["config", "get", "model"])
    # Assert
    assert set_result.exit_code == ExitCode.OK
    assert get_result.stdout.strip() == "jev-1.13"
    assert services.settings.load().profiles["default"].model == "jev-1.13"


def test_config_set_numbers_are_validated(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    runner.invoke(cli, ["config", "set", "timeout", "12.5"])
    runner.invoke(cli, ["config", "set", "max_retries", "3"])
    # Act
    bad_timeout = runner.invoke(cli, ["config", "set", "timeout", "0"])
    bad_retries = runner.invoke(cli, ["config", "set", "max_retries", "-1"])
    # Assert
    profile = services.settings.load().profiles["default"]
    assert (profile.timeout, profile.max_retries) == (12.5, 3)
    assert bad_timeout.exit_code == bad_retries.exit_code == ExitCode.USAGE


def test_config_set_changing_provider_drops_host_settings(
    runner: CliRunner, cli: typer.Typer, services: Services
) -> None:
    # Arrange
    services.settings.save(
        Settings(profiles={"default": Profile(model="jev-1.13", base_url="https://proxy.example.com")})
    )
    # Act
    result = runner.invoke(cli, ["config", "set", "provider", "openrouter"])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert services.settings.load().profiles["default"] == Profile(provider=Provider.OPENROUTER)


def test_config_set_rejects_unknown_provider_and_key(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    commands = [["config", "set", "provider", "nope"], ["config", "set", "colour", "red"], ["config", "get", "colour"]]
    # Act
    codes = [runner.invoke(cli, command).exit_code for command in commands]
    # Assert
    assert codes == [ExitCode.USAGE] * 3


def test_config_set_output_is_global_and_unset_clears_it(
    runner: CliRunner, cli: typer.Typer, services: Services
) -> None:
    # Arrange
    runner.invoke(cli, ["config", "set", "output", "csv"])
    after_set = services.settings.load().output
    # Act
    result = runner.invoke(cli, ["config", "unset", "output"])
    # Assert
    assert (after_set, services.settings.load().output) == ("csv", None)
    assert result.exit_code == ExitCode.OK


def test_config_unset_restores_the_default(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(Settings(profiles={"default": Profile(model="jev-1.13")}))
    # Act
    runner.invoke(cli, ["config", "unset", "model"])
    result = runner.invoke(cli, ["config", "get", "model"])
    # Assert
    assert services.settings.load().profiles["default"].model is None
    assert not result.stdout


def test_config_get_output_reads_the_global_setting(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(Settings(output="json"))
    # Act
    result = runner.invoke(cli, ["config", "get", "output"])
    # Assert
    assert result.stdout.strip() == "json"
