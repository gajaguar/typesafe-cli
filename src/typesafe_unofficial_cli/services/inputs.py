from __future__ import annotations

import contextlib
import json
import re
import sys
from enum import StrEnum
from typing import TYPE_CHECKING
from typing import Final
from typing import cast

import yaml

from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from pathlib import Path

    from typesafe_sdk import JSONContent
    from typesafe_sdk import JSONValue
    from typesafe_sdk import QuestionModel

STDIN_MARKER: Final = "-"
_QUESTION_TYPES: Final = frozenset({"noul", "choice", "score"})
_YAML_SUFFIXES: Final = frozenset({".yaml", ".yml"})
_BOOL_TAG: Final = "tag:yaml.org,2002:bool"
_YAML_11_TAGS: Final = frozenset({_BOOL_TAG, "tag:yaml.org,2002:timestamp"})


# PyYAML follows YAML 1.1, where yes/no/on/off load as booleans and dates as date objects. Neither is
# JSON-compatible nor what a question file means, so only true/false stay booleans and the rest stay text.
class _YamlLoader(yaml.SafeLoader):
    pass


def _yaml_12_resolvers() -> dict[str, list[tuple[str, re.Pattern[str]]]]:
    return {
        first: [(tag, pattern) for tag, pattern in resolvers if tag not in _YAML_11_TAGS]
        for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


_YamlLoader.yaml_implicit_resolvers = _yaml_12_resolvers()
_YamlLoader.add_implicit_resolver(_BOOL_TAG, re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


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


def _parse_yaml(raw: str, *, label: str) -> object:
    try:
        return yaml.load(raw, Loader=_YamlLoader)  # ruff: ignore[unsafe-yaml-load]  # the loader extends SafeLoader
    except yaml.YAMLError as error:
        message = f"{label} is not valid YAML: {error}"
        raise CliError(message, exit_code=ExitCode.USAGE) from error


# A .yaml/.yml file is YAML, standard input is JSON when it parses as such and YAML otherwise, and
# any other file is JSON.
def _parse_document(raw: str, *, source: Path, label: str) -> object:
    if str(source) == STDIN_MARKER:
        with contextlib.suppress(ValueError):
            return json.loads(raw)
        try:
            return yaml.load(raw, Loader=_YamlLoader)  # ruff: ignore[unsafe-yaml-load]  # the loader extends SafeLoader
        except yaml.YAMLError as error:
            message = f"{label} is neither valid JSON nor valid YAML: {error}"
            raise CliError(message, exit_code=ExitCode.USAGE) from error
    if source.suffix.lower() in _YAML_SUFFIXES:
        return _parse_yaml(raw, label=label)
    return _parse_json(raw, label=label)


# JSON keys are always text, so a YAML key that loaded as a number, boolean or date cannot be sent.
def _require_text_keys(value: object, *, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                message = f"{label} has the key {key!r}, which is not text; quote it."
                raise CliError(message, exit_code=ExitCode.USAGE)
            _require_text_keys(item, label=label)
    elif isinstance(value, list):
        for item in value:
            _require_text_keys(item, label=label)


# An unquoted `true:` or `false:` noul criterion loads as a boolean key.
def _text_noul_criteria(question: object) -> None:
    if not isinstance(question, dict) or question.get("type") != "noul":
        return
    criteria = question.get("criteria")
    if isinstance(criteria, dict):
        question["criteria"] = {
            str(key).lower() if isinstance(key, bool) else key: value for key, value in criteria.items()
        }


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
    payload = _parse_document(_read_text(file), source=file, label="The questions file")
    if not isinstance(payload, dict) or not payload:
        message = "The questions file must be a non-empty object keyed by question name."
        raise CliError(message, exit_code=ExitCode.USAGE)
    for question in payload.values():
        _text_noul_criteria(question)
    _require_text_keys(payload, label="The questions file")
    for name, question in payload.items():
        if not isinstance(question, dict) or question.get("type") not in _QUESTION_TYPES:
            message = f'Question "{name}" needs a "type" of noul, choice or score.'
            raise CliError(message, exit_code=ExitCode.USAGE)
        if question["type"] != "noul" and not question.get("criteria"):
            message = f'Question "{name}" ({question["type"]}) needs non-empty "criteria".'
            raise CliError(message, exit_code=ExitCode.USAGE)
    return cast("dict[str, QuestionModel]", payload)


# One state per non-blank line, each a JSON value: a string, an object or an array.
def read_states(file: Path) -> list[JSONContent]:
    states: list[JSONContent] = []
    for number, line in enumerate(_read_text(file).splitlines(), start=1):
        if not line.strip():
            continue
        content = _parse_json(line, label=f"Line {number} of the states file")
        if not isinstance(content, str | dict | list) or not content:
            message = f"Line {number} of the states file must be a non-empty JSON string, object or array."
            raise CliError(message, exit_code=ExitCode.USAGE)
        states.append(cast("JSONContent", content))
    if not states:
        message = "The states file has no states."
        raise CliError(message, exit_code=ExitCode.USAGE)
    return states


def read_extra_body(file: Path) -> dict[str, JSONValue | None]:
    payload = _parse_document(_read_text(file), source=file, label="The extra body")
    if not isinstance(payload, dict):
        message = "The extra body must be an object."
        raise CliError(message, exit_code=ExitCode.USAGE)
    _require_text_keys(payload, label="The extra body")
    return cast("dict[str, JSONValue | None]", payload)
