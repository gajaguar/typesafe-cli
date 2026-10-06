from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Final

import httpx2
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


def test_ask_header_flag_reaches_the_api(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--header", "X-Trace: abc"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.requests[0].headers["X-Trace"] == "abc"


@pytest.mark.parametrize("header", ["Authorization: Bearer x", "no-separator"])
def test_ask_rejects_unusable_headers(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, header: str
) -> None:
    # Arrange
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--header", header]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert not api.requests


def test_ask_extra_body_is_merged_into_the_request(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, tmp_path: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    extra = tmp_path / "extra.json"
    extra.write_text('{"seed": 7}', encoding="utf-8")
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--extra-body", str(extra)]
    # Act
    runner.invoke(cli, args)
    # Assert
    assert api.bodies()[0]["seed"] == 7


def test_ask_extra_body_must_be_an_object(
    runner: CliRunner, cli: typer.Typer, questions_file: Path, tmp_path: Path
) -> None:
    # Arrange
    extra = tmp_path / "extra.json"
    extra.write_text("[1]", encoding="utf-8")
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--extra-body", str(extra)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE


def test_ask_profile_timeout_and_retries_reach_the_client(
    runner: CliRunner, cli: typer.Typer, services: Services, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    services.settings.save(Settings(profiles={"default": Profile(timeout=3, max_retries=1)}))
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(questions_file), "--timeout", "5"])
    # Assert
    assert result.exit_code == ExitCode.OK


def test_ask_prints_the_request_id_on_stderr_and_in_records(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.handler = lambda _request: httpx2.Response(
        200, json=SYSTEM_ONE_PAYLOAD, headers={"x-typesafe-request-id": "req_1"}
    )
    args = ["-o", "json", "ask", "--state", "x", "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert "request id: req_1" in result.stderr
    assert {row["request_id"] for row in json.loads(result.stdout)} == {"req_1"}


@pytest.fixture(name="states_file")
def states_file_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "states.jsonl"
    path.write_text('"first"\n\n{"message": "second"}\n', encoding="utf-8")
    return path


def test_ask_batch_answers_every_state_in_input_order(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, states_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["-o", "json", "ask", "--states-file", str(states_file), "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert [row["index"] for row in json.loads(result.stdout)] == [0, 0, 0, 1, 1, 1]
    assert {json.dumps(body["state"]) for body in api.bodies()} == {'"first"', '{"message": "second"}'}
    assert "answered: 2" in result.stderr


def _reject_first_state(request: httpx2.Request) -> httpx2.Response:
    if json.loads(request.content)["state"] == "first":
        return httpx2.Response(401, json={"detail": "bad key"})
    return httpx2.Response(200, json=SYSTEM_ONE_PAYLOAD)


def test_ask_batch_reports_failed_states_and_keeps_the_rest(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, states_file: Path
) -> None:
    # Arrange
    api.handler = _reject_first_state
    args = ["-o", "json", "ask", "--states-file", str(states_file), "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.AUTHENTICATION
    assert {row["index"] for row in json.loads(result.stdout)} == {1}
    assert "state 0:" in result.stderr


def test_ask_batch_conflicts_with_a_single_state(
    runner: CliRunner, cli: typer.Typer, questions_file: Path, states_file: Path
) -> None:
    # Arrange
    args = ["ask", "--state", "x", "--states-file", str(states_file), "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE


@pytest.mark.parametrize("content", ["", "5\n", "not json\n"])
def test_ask_batch_rejects_unusable_states_files(
    runner: CliRunner, cli: typer.Typer, questions_file: Path, tmp_path: Path, content: str
) -> None:
    # Arrange
    path = tmp_path / "bad.jsonl"
    path.write_text(content, encoding="utf-8")
    args = ["ask", "--states-file", str(path), "--questions-file", str(questions_file)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE


def test_ask_rejects_two_sources_reading_standard_input(
    runner: CliRunner, cli: typer.Typer, questions_file: Path
) -> None:
    # Arrange
    args = ["ask", "--states-file", "-", "--questions-file", "-"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert "--states-file" in result.stderr


_FLAG_QUESTIONS: Final = [
    "--noul",
    "billing=Is this about billing?",
    "--choice",
    "tone=What is the tone?",
    "--criterion",
    "tone=calm",
    "--criterion",
    "tone=angry",
    "--score",
    "urgency=How urgent is it?",
    "--criterion",
    "urgency=low",
    "--criterion",
    "urgency=medium",
    "--criterion",
    "urgency=high",
]


@pytest.mark.usefixtures("api_key")
def test_ask_question_flags_build_the_same_questions_as_a_file(
    runner: CliRunner, cli: typer.Typer, api: FakeApi
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["ask", "--state", "I was charged twice.", *_FLAG_QUESTIONS])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["questions"] == QUESTIONS


@pytest.mark.usefixtures("api_key")
def test_ask_criterion_descriptions_split_on_the_first_colon_except_for_score(
    runner: CliRunner, cli: typer.Typer, api: FakeApi
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = [
        *("--noul", "billing=Billing?", "--criterion", "billing=true:Yes: charged", "--criterion", "billing=false"),
        *("--choice", "tone=Tone?", "--criterion", "tone=calm", "--criterion", "tone=angry:Hostile: upset"),
        *("--score", "urgency=Urgent?", "--criterion", "urgency=low: not now", "--criterion", "urgency=high"),
    ]
    # Act
    runner.invoke(cli, ["ask", "--state", "x", *args])
    # Assert
    assert api.bodies()[0]["questions"] == {
        "billing": {"type": "noul", "instructions": "Billing?", "criteria": {"true": "Yes: charged", "false": None}},
        "tone": {"type": "choice", "instructions": "Tone?", "criteria": {"calm": None, "angry": "Hostile: upset"}},
        "urgency": {"type": "score", "instructions": "Urgent?", "criteria": ["low: not now", "high"]},
    }


def test_ask_question_flag_replaces_the_file_question_with_the_same_name(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--noul", "billing=Is it a refund?"]
    # Act
    runner.invoke(cli, args)
    # Assert
    assert api.bodies()[0]["questions"] == {
        **QUESTIONS,
        "billing": {"type": "noul", "instructions": "Is it a refund?"},
    }


@pytest.mark.usefixtures("api_key")
def test_ask_batch_accepts_question_flags_alone(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, states_file: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["ask", "--states-file", str(states_file), *_FLAG_QUESTIONS])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert [body["questions"] for body in api.bodies()] == [QUESTIONS, QUESTIONS]


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--noul", "billing"], id="no-equals"),
        pytest.param(["--noul", "=Is it?"], id="empty-name"),
        pytest.param(["--noul", "billing="], id="empty-instructions"),
        pytest.param(["--noul", "q=A?", "--score", "q=B?", "--criterion", "q=low"], id="duplicate-name"),
        pytest.param(["--noul", "q=A?", "--criterion", "other=true"], id="orphan-criterion"),
        pytest.param(["--choice", "q=A?"], id="choice-without-criteria"),
        pytest.param(["--score", "q=A?"], id="score-without-criteria"),
        pytest.param(["--noul", "q=A?", "--criterion", "q=maybe"], id="noul-unknown-label"),
        pytest.param(["--noul", "q=A?", "--criterion", "q=true", "--criterion", "q=true"], id="noul-repeated-label"),
        pytest.param(["--choice", "q=A?", "--criterion", "q=:note"], id="choice-empty-label"),
        pytest.param(["--choice", "q=A?", "--criterion", "q=a", "--criterion", "q=a"], id="choice-repeated-label"),
        pytest.param(["--score", "q=A?", "--criterion", "q="], id="score-empty-level"),
    ],
)
@pytest.mark.usefixtures("api_key")
def test_ask_invalid_question_flags_exit_usage_without_a_request(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, args: list[str]
) -> None:
    # Arrange
    argv = ["ask", "--state", "x", *args]
    # Act
    result = runner.invoke(cli, argv)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


YAML_QUESTIONS: Final = """\
billing:
  type: noul
  instructions: Is this billing?
  criteria:
    true: A charge.
    false: Something else.
tone:
  type: choice
  instructions: What is the tone?
  criteria:
    calm: Neutral.
    angry: Upset.
urgency:
  type: score
  instructions: How urgent is it?
  criteria:
    - Low.
    - High.
"""
YAML_EXPECTED: Final = {
    "billing": {
        "type": "noul",
        "instructions": "Is this billing?",
        "criteria": {"true": "A charge.", "false": "Something else."},
    },
    "tone": {
        "type": "choice",
        "instructions": "What is the tone?",
        "criteria": {"calm": "Neutral.", "angry": "Upset."},
    },
    "urgency": {"type": "score", "instructions": "How urgent is it?", "criteria": ["Low.", "High."]},
}


@pytest.mark.parametrize("name", ["questions.yaml", "questions.yml", "QUESTIONS.YAML"])
def test_ask_reads_questions_from_a_yaml_file(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None, tmp_path: Path, name: str
) -> None:
    del api_key
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    path = tmp_path / name
    path.write_text(YAML_QUESTIONS, encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["questions"] == YAML_EXPECTED


def test_ask_reads_yaml_questions_from_stdin(runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None) -> None:
    del api_key
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", "-"], input=YAML_QUESTIONS)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["questions"] == YAML_EXPECTED


def test_ask_json_file_is_not_read_as_yaml(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None, tmp_path: Path
) -> None:
    del api_key
    # Arrange
    path = tmp_path / "questions.json"
    path.write_text(YAML_QUESTIONS, encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


def test_ask_yaml_keeps_yes_no_and_dates_as_text(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None, tmp_path: Path
) -> None:
    del api_key
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    path = tmp_path / "questions.yaml"
    path.write_text(
        "q:\n  type: choice\n  instructions: Pick one.\n  criteria:\n    yes: on\n    no: 2026-10-05\n    off: ~\n",
        encoding="utf-8",
    )
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["questions"]["q"]["criteria"] == {"yes": "on", "no": "2026-10-05", "off": None}


@pytest.mark.parametrize(
    "questions",
    [
        pytest.param("1:\n  type: noul\n  instructions: x\n", id="numeric-name"),
        pytest.param("true:\n  type: noul\n  instructions: x\n", id="boolean-name"),
        pytest.param("q:\n  type: choice\n  instructions: x\n  criteria:\n    1: one\n", id="numeric-criterion"),
        pytest.param("q: [unclosed\n", id="invalid-yaml"),
        pytest.param("- a\n- b\n", id="not-an-object"),
    ],
)
def test_ask_invalid_yaml_questions_exit_usage_without_a_request(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None, tmp_path: Path, questions: str
) -> None:
    del api_key
    # Arrange
    path = tmp_path / "bad.yaml"
    path.write_text(questions, encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


def test_ask_stdin_that_is_neither_json_nor_yaml_exits_usage(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None
) -> None:
    del api_key
    # Arrange
    args = ["ask", "--state", "x", "--questions-file", "-"]
    # Act
    result = runner.invoke(cli, args, input="q: [unclosed\n")
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


def test_ask_extra_body_is_read_from_yaml(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, tmp_path: Path
) -> None:
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    extra = tmp_path / "extra.yaml"
    extra.write_text("seed: 7\nprovider:\n  order: [openai]\n", encoding="utf-8")
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--extra-body", str(extra)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.bodies()[0]["seed"] == 7
    assert api.bodies()[0]["provider"] == {"order": ["openai"]}


@pytest.mark.parametrize("content", ["- 1\n", "1: one\n", "a: [unclosed\n"])
def test_ask_invalid_yaml_extra_body_exits_usage(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, questions_file: Path, tmp_path: Path, content: str
) -> None:
    # Arrange
    extra = tmp_path / "extra.yml"
    extra.write_text(content, encoding="utf-8")
    args = ["ask", "--state", "x", "--questions-file", str(questions_file), "--extra-body", str(extra)]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE
    assert api.requests == []


@pytest.mark.parametrize("template_format", ["json", "yaml", "YAML"])
def test_ask_questions_template_prints_a_file_ask_accepts(
    runner: CliRunner, cli: typer.Typer, api: FakeApi, api_key: None, tmp_path: Path, template_format: str
) -> None:
    del api_key
    # Arrange
    api.respond(200, SYSTEM_ONE_PAYLOAD)
    printed = runner.invoke(cli, ["ask", "--questions-template", template_format])
    path = tmp_path / f"questions.{template_format.lower()}"
    path.write_text(printed.stdout, encoding="utf-8")
    # Act
    result = runner.invoke(cli, ["ask", "--state", "x", "--questions-file", str(path)])
    # Assert
    questions = api.bodies()[0]["questions"]
    assert printed.exit_code == ExitCode.OK
    assert result.exit_code == ExitCode.OK
    assert {question["type"] for question in questions.values()} == {"noul", "choice", "score"}
    assert all(question["instructions"] for question in questions.values())
    assert set(questions["billing"]["criteria"]) == {"true", "false"}


def test_ask_questions_template_needs_no_credentials_or_state(
    runner: CliRunner, cli: typer.Typer, api: FakeApi
) -> None:
    # Arrange
    args = ["ask", "--questions-template", "yaml"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.OK
    assert api.requests == []


def test_ask_questions_template_rejects_an_unknown_format(runner: CliRunner, cli: typer.Typer) -> None:
    # Arrange
    args = ["ask", "--questions-template", "toml"]
    # Act
    result = runner.invoke(cli, args)
    # Assert
    assert result.exit_code == ExitCode.USAGE
