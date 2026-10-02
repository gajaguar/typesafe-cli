from __future__ import annotations

import json
import sys
from enum import StrEnum
from typing import TYPE_CHECKING
from typing import Final
from typing import cast

from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from pathlib import Path

    from typesafe_sdk import JSONContent
    from typesafe_sdk import QuestionModel

STDIN_MARKER: Final = "-"
_QUESTION_TYPES: Final = frozenset({"noul", "choice", "score"})


class StateFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


def _read_text(source: Path) -> str:
    if str(source) == STDIN_MARKER:
        return sys.stdin.read()
    try:
        return source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        message = f"Cannot read {source}: {error}"
        raise CliError(message, exit_code=ExitCode.USAGE) from error


def _parse_json(raw: str, *, label: str) -> object:
    try:
        return json.loads(raw)
    except ValueError as error:
        message = f"{label} is not valid JSON: {error}"
        raise CliError(message, exit_code=ExitCode.USAGE) from error


def read_state(*, text: str | None, file: Path | None, state_format: StateFormat) -> JSONContent:
    if (text is None) == (file is None):
        message = "Pass exactly one of --state and --state-file."
        raise CliError(message, exit_code=ExitCode.USAGE)
    raw = text if text is not None else _read_text(cast("Path", file))
    if state_format is StateFormat.TEXT:
        content: object = raw
    else:
        content = _parse_json(raw, label="The state")
    if not isinstance(content, str | dict | list):
        message = "The state must be text, a JSON object or a JSON array."
        raise CliError(message, exit_code=ExitCode.USAGE)
    if not content:
        message = "The state is empty."
        raise CliError(message, exit_code=ExitCode.USAGE)
    return cast("JSONContent", content)


# Same shape as the SDK's question dictionaries: {"<name>": {"type": "noul|choice|score", ...}}.
def read_questions(file: Path) -> dict[str, QuestionModel]:
    payload = _parse_json(_read_text(file), label="The questions file")
    if not isinstance(payload, dict) or not payload:
        message = "The questions file must be a non-empty JSON object keyed by question name."
        raise CliError(message, exit_code=ExitCode.USAGE)
    for name, question in payload.items():
        if not isinstance(question, dict) or question.get("type") not in _QUESTION_TYPES:
            message = f'Question "{name}" needs a "type" of noul, choice or score.'
            raise CliError(message, exit_code=ExitCode.USAGE)
        if question["type"] != "noul" and not question.get("criteria"):
            message = f'Question "{name}" ({question["type"]}) needs non-empty "criteria".'
            raise CliError(message, exit_code=ExitCode.USAGE)
    return cast("dict[str, QuestionModel]", payload)
