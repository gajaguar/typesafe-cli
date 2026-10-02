from __future__ import annotations

from typing import TYPE_CHECKING

from typesafe_unofficial_cli import __version__
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    import typer
    from typer.testing import CliRunner

    from typesafe_unofficial_cli.runtime.context import Services


def test_version_flag_prints_version(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["--version"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert result.stdout == f"typesafe {__version__}\n"


def test_no_arguments_shows_commands(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args: list[str] = []
    # Act
    result = runner.invoke(cli, args)
    # Assert
    for name in ("auth", "config", "models", "ask"):
        assert name in result.output


def test_corrupt_settings_file_exits_with_configuration_code(
    runner: CliRunner, cli: typer.Typer, services: Services
) -> None:
    # Arrange
    services.settings.path.write_text("not = [valid", encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["config", "list"])
    # Assert
    assert result.exit_code == ExitCode.CONFIGURATION
    assert "Cannot parse" in result.stderr


def test_piped_output_defaults_to_json(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["config", "list"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert result.stdout == "[]\n"


def test_verbose_flag_is_accepted(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["-v", "config", "list"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
