from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.conftest import QUESTIONS
from tests.conftest import SYSTEM_ONE_PAYLOAD
from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from pathlib import Path

    import typer
    from typer.testing import CliRunner

    from tests.conftest import FakeApi
    from typesafe_unofficial_cli.runtime.context import Services


@pytest.fixture(name="questions_file")
def questions_file_fixture(tmp_path: Path, api_key: None) -> Path:
    del api_key
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    return path


@pytest.fixture(name="api_key")
def api_key_fixture(environ: dict[str, str]) -> None:
    environ["TYPESAFE_API_KEY"] = "secret"


def test_ask_json_has_one_record_per_question(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["-o", "json", "ask", "--state", "I was charged twice.", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    rows = json.loads(result.stdout)
    answers = {row["question"]: row["answer"] for row in rows}
    assert answers == {"billing": pytest.approx(0.93), "tone": "angry", "urgency": pytest.approx(2.4)}
    legends = {row["question"]: row["legend"] for row in rows if row.get("legend")}
    assert legends == {"urgency": {"0": "low", "1": "medium", "2": "high"}}


def test_ask_sends_state_questions_and_default_model(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["ask", "--state", "I was charged twice.", "--questions-file", str(questions_file)]
    # Act
    runner.invoke(cli, args)
    # Assert
    assert api.bodies() == [{"state": "I was charged twice.", "model": "jev-latest", "questions": QUESTIONS}]


def test_ask_model_flag_overrides_profile_model(
    runner: CliRunner, cli: typer.Typer, services: Services, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    services.settings.save(Settings(profiles={"default": Profile(model="jev-1.12")}))
    base = ["ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    runner.invoke(cli, base)
    runner.invoke(cli, [*base, "--model", "jev-1.13"])
    # Assert
    assert [body["model"] for body in api.bodies()] == ["jev-1.12", "jev-1.13"]


def test_ask_on_openrouter_profile_uses_its_host_and_key(
    runner: CliRunner,
    cli: typer.Typer,
    services: Services,
    environ: dict[str, str],
    api: FakeApi,
    questions_file: Path,
) -> None:
    # Arrange
    environ["OPENROUTER_API_KEY"] = "or-secret"
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    services.settings.save(Settings(profiles={"default": Profile(provider=Provider.OPENROUTER)}))
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(questions_file)])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert str(api.requests[0].url) == "https://openrouter.ai/api/v1/systemone"
    assert api.requests[0].headers["authorization"] == "Bearer or-secret"


def test_ask_reports_model_and_usage_on_stderr_only(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["-o", "json", "ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert "model: jev-1.13 | input tokens: 12 | output tokens: 3" in result.stderr
    assert "input tokens" not in result.stdout


def test_ask_reads_json_state_from_stdin(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["ask", "--state-file", "-", "--state-format", "json", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args, input='{"message": "I was charged twice."}')
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["state"] == {"message": "I was charged twice."}


def test_ask_reads_questions_from_stdin(runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None) -> None:
    del api_key
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["ask", "--state", "x", "--questions-file", "-"]
    # Act
    result = runner.invoke(cli, args, input=json.dumps(QUESTIONS))
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["questions"] == QUESTIONS


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--state", "x"], id="no-questions"),
        pytest.param(["--questions-file", "{q}"], id="no-state"),
        pytest.param(["--state", "x", "--state-file", "{q}", "--questions-file", "{q}"], id="two-states"),
        pytest.param(["--state-file", "-", "--questions-file", "-"], id="both-stdin"),
        pytest.param(["--state", "x", "--state-format", "json", "--questions-file", "{q}"], id="state-not-json"),
        pytest.param(["--state", "", "--questions-file", "{q}"], id="empty-state"),
        pytest.param(["--state", "x", "--questions-file", "/no/such/file.json"], id="missing-file"),
    ],
)
def test_ask_input_mistakes_exit_usage_without_a_request(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, args: list[str]
) -> None:
    # Arrange
    argv = ["ask", *(arg.replace("{q}", str(questions_file)) for arg in args)]
    # Act
    result = runner.invoke(cli, argv)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


@pytest.mark.parametrize(
    "questions",
    [
        pytest.param("[]", id="not-an-object"),
        pytest.param("{}", id="empty"),
        pytest.param("not json", id="invalid-json"),
        pytest.param('{"q": {"type": "essay"}}', id="unknown-type"),
        pytest.param('{"q": "text"}', id="not-a-question"),
        pytest.param('{"q": {"type": "choice"}}', id="choice-without-criteria"),
        pytest.param('{"q": {"type": "score", "criteria": []}}', id="score-without-levels"),
    ],
)
def test_ask_invalid_questions_exit_usage(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, tmp_path: Path, questions: str
) -> None:
    # Arrange
    path = tmp_path / "bad.json"
    path.write_text(questions, encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [
        (401, ExitCode.AUTHENTICATION),
        (403, ExitCode.FORBIDDEN),
        (404, ExitCode.NOT_FOUND),
        (400, ExitCode.VALIDATION),
        (422, ExitCode.VALIDATION),
        (429, ExitCode.RATE_LIMITED),
        (500, ExitCode.UNAVAILABLE),
        (529, ExitCode.UNAVAILABLE),
        (418, ExitCode.FAILURE),
    ],
)
def test_ask_maps_http_failures_to_exit_codes(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, status: int, exit_code: ExitCode
) -> None:
    # Arrange
    api.respond(status, {"detail": "nope"})
    args = ["ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == exit_code
    assert result.stderr.startswith("error:")


def test_ask_malformed_success_body_exits_unavailable(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, {"unexpected": True})
    args = ["ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.UNAVAILABLE


def test_ask_table_output_lists_answers(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["-o", "csv", "ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.stdout.splitlines()[:2] == ["Question,Type,Answer,Confidence", "billing,noul,0.93,"]
