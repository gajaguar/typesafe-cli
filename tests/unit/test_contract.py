from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Final

import typer

from tests.conftest import MODELS_PAYLOAD
from tests.conftest import QUESTIONS
from tests.conftest import SYSTEM_ONE_PAYLOAD
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner

    from tests.conftest import FakeApi
    from typesafe_unofficial_cli.runtime.context import Services

# The 1.0.0 public contract: a change here is a breaking change and needs a major bump
# (see docs/conventions/public-contract.md).
COMMAND_SURFACE: Final = {
    "typesafe": (["--output", "--profile", "--verbose", "--version", "-o", "-p", "-v"], []),
    "ask": (
        [
            "--choice",
            "--concurrency",
            "--criterion",
            "--extra-body",
            "--header",
            "--max-retries",
            "--model",
            "--noul",
            "--questions-file",
            "--score",
            "--state",
            "--state-file",
            "--state-format",
            "--states-file",
            "--timeout",
        ],
        [],
    ),
    "auth login": (["--base-url", "--insecure-storage", "--provider", "--skip-validation", "--with-token"], []),
    "auth logout": ([], []),
    "auth status": (["--check"], []),
    "auth token": ([], []),
    "config get": ([], ["key"]),
    "config list": ([], []),
    "config path": ([], []),
    "config set": ([], ["key", "value"]),
    "config unset": ([], ["key"]),
    "config use": ([], ["name"]),
    "models list": (["--header", "--max-retries", "--timeout"], []),
}

EXIT_CODES: Final = {
    "OK": 0,
    "FAILURE": 1,
    "USAGE": 2,
    "CONFIGURATION": 3,
    "AUTHENTICATION": 4,
    "FORBIDDEN": 5,
    "NOT_FOUND": 6,
    "VALIDATION": 7,
    "RATE_LIMITED": 8,
    "UNAVAILABLE": 9,
}

# Typer adds the completion options itself; they are not part of the contract.
GENERATED_OPTIONS: Final = frozenset({"--install-completion", "--show-completion"})


def _surface(command: object, path: tuple[str, ...] = ()) -> dict[str, tuple[list[str], list[str]]]:
    options = sorted(
        name
        for param in command.params  # type: ignore[attr-defined]
        if param.param_type_name == "option"
        for name in (*param.opts, *param.secondary_opts)
        if name not in GENERATED_OPTIONS
    )
    arguments = [param.name for param in command.params if param.param_type_name == "argument"]  # type: ignore[attr-defined]
    children = getattr(command, "commands", {})
    surface = {} if children else {" ".join(path) or "typesafe": (options, arguments)}
    if not path:
        surface["typesafe"] = (options, arguments)
    for name, child in children.items():
        surface.update(_surface(child, (*path, name)))
    return surface


def test_command_and_option_names_are_the_frozen_surface(cli: typer.Typer) -> None:
    # Arrange
    command = typer.main.get_command(cli)
    # Act
    surface = _surface(command)
    # Assert
    assert surface == COMMAND_SURFACE


def test_exit_codes_keep_their_values() -> None:
    # Arrange
    expected = EXIT_CODES
    # Act
    actual = {code.name: int(code) for code in ExitCode}
    # Assert
    assert actual == expected


def test_ask_record_fields(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, environ: dict[str, str], tmp_path: Path
) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    questions = tmp_path / "q.json"
    questions.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    args = ["-o", "json", "ask", "--state", "x", "--questions-file", str(questions)]
    # Act
    rows = {row["type"]: sorted(row) for row in json.loads(runner.invoke(cli, args).stdout)}
    # Assert
    assert rows == {
        "noul": ["answer", "noul", "question", "request_id", "type"],
        "choice": ["answer", "choice", "confidence", "probabilities", "question", "request_id", "type"],
        "score": ["answer", "confidence", "legend", "probabilities", "question", "request_id", "score", "type"],
    }


def test_models_list_record_fields(runner: CliRunner, cli: typer.Typer, api: FakeApi, environ: dict[str, str]) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    api.respond(200, MODELS_PAYLOAD)
    # Act
    rows = json.loads(runner.invoke(cli, ["-o", "json", "models", "list"]).stdout)
    # Assert
    assert sorted(rows[0]) == ["description", "name", "release_date"]


def test_auth_status_record_fields(runner: CliRunner, cli: typer.Typer, environ: dict[str, str]) -> None:
    # Arrange
    environ["TYPESAFE_API_KEY"] = "secret"
    # Act
    record = json.loads(runner.invoke(cli, ["-o", "json", "auth", "status"]).stdout)
    # Assert
    assert sorted(record) == ["api_key", "base_url", "model", "profile", "provider", "source"]


def test_config_list_record_fields(runner: CliRunner, cli: typer.Typer, services: Services) -> None:
    # Arrange
    services.settings.save(Settings(profiles={"a": Profile()}))
    # Act
    rows = json.loads(runner.invoke(cli, ["-o", "json", "config", "list"]).stdout)
    # Assert
    assert sorted(rows[0]) == ["base_url", "default", "model", "name", "provider"]
