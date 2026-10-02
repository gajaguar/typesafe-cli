from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final
from typing import NoReturn
from typing import cast

from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from typesafe_sdk import QuestionModel

_NOUL_LABELS: Final = ("true", "false")


def _fail(message: str) -> NoReturn:
    raise CliError(message, exit_code=ExitCode.USAGE)


def _split(item: str, flag: str) -> tuple[str, str]:
    name, separator, value = item.partition("=")
    name = name.strip()
    if not separator or not name or not value.strip():
        _fail(f"{flag} '{item}' must look like 'name=value'.")
    return name, value.strip()


# `label:description` splits on the first colon; the description is optional.
def _label_and_description(value: str) -> tuple[str, str | None]:
    label, _, description = value.partition(":")
    return label.strip(), description.strip() or None


def _noul_criteria(name: str, values: list[str]) -> dict[str, str | None]:
    criteria: dict[str, str | None] = {}
    for value in values:
        label, description = _label_and_description(value)
        if label not in _NOUL_LABELS or label in criteria:
            _fail(f'Noul question "{name}" takes at most one --criterion each for {" and ".join(_NOUL_LABELS)}.')
        criteria[label] = description
    return criteria


def _choice_criteria(name: str, values: list[str]) -> dict[str, str | None]:
    criteria: dict[str, str | None] = {}
    for value in values:
        label, description = _label_and_description(value)
        if not label or label in criteria:
            _fail(f'Choice question "{name}" needs distinct, non-empty criterion labels.')
        criteria[label] = description
    return criteria


def _add_criteria(name: str, question: dict[str, object], values: list[str]) -> None:
    if question["type"] == "noul":
        if values:
            question["criteria"] = _noul_criteria(name, values)
    elif not values:
        _fail(f'Question "{name}" ({question["type"]}) needs at least one --criterion.')
    elif question["type"] == "choice":
        question["criteria"] = _choice_criteria(name, values)
    else:
        # The flag order fixes the score, so each value is kept whole, colons included.
        question["criteria"] = values


def build_questions(
    *, noul: list[str], choice: list[str], score: list[str], criterion: list[str]
) -> dict[str, QuestionModel]:
    questions: dict[str, dict[str, object]] = {}
    for kind, items in (("noul", noul), ("choice", choice), ("score", score)):
        for item in items:
            name, instructions = _split(item, f"--{kind}")
            if name in questions:
                _fail(f'Question "{name}" is defined more than once.')
            questions[name] = {"type": kind, "instructions": instructions}
    criteria: dict[str, list[str]] = {}
    for item in criterion:
        name, value = _split(item, "--criterion")
        if name not in questions:
            _fail(f'--criterion names "{name}", which no --noul, --choice or --score defines.')
        criteria.setdefault(name, []).append(value)
    for name, question in questions.items():
        _add_criteria(name, question, criteria.get(name, []))
    return cast("dict[str, QuestionModel]", questions)
