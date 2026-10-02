from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from typesafe_sdk import ChoiceAnswer
from typesafe_sdk import NoulAnswer
from typesafe_sdk import ScoreAnswer

if TYPE_CHECKING:
    from typesafe_sdk import Answer
    from typesafe_sdk import SystemOneResponse

    from typesafe_unofficial_cli.output.renderer import Record

_UNREPORTED: Final = "?"


def _value(answer: Answer) -> object:
    match answer:
        case NoulAnswer():
            return answer.noul
        case ChoiceAnswer():
            return answer.choice
        case ScoreAnswer():
            return answer.score


# One record per question: the API's own answer fields plus `question` (its name) and `answer`
# (the noul, choice or score value), so a table and a script can read the result the same way.
def answer_records(response: SystemOneResponse) -> list[Record]:
    records: list[Record] = []
    for name, answer in response.answers.items():
        record: dict[str, object] = {"question": name, "answer": _value(answer)}
        record.update(answer.model_dump(mode="json"))
        records.append(record)
    return records


# Model and token usage are not part of the rows, so they go to stderr like any other diagnostic.
def usage_line(response: SystemOneResponse) -> str:
    usage = response.usage
    input_tokens = _UNREPORTED if usage.input_tokens is None else usage.input_tokens
    output_tokens = _UNREPORTED if usage.output_tokens is None else usage.output_tokens
    return f"model: {response.model} | input tokens: {input_tokens} | output tokens: {output_tokens}"
