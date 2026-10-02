from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from typesafe_sdk import ChoiceAnswer
from typesafe_sdk import NoulAnswer
from typesafe_sdk import ScoreAnswer
from typesafe_sdk import TypeSafeError

if TYPE_CHECKING:
    from collections.abc import Sequence

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


def request_id_of(response: SystemOneResponse) -> str | None:
    try:
        return response.request_id
    except TypeSafeError:
        return None


# One record per question: the API's own answer fields plus `question` (its name), `answer`
# (the noul, choice or score value) and the response's `request_id`, so a table and a script can
# read the result the same way. A batch adds the `index` of the state each answer belongs to.
def answer_records(response: SystemOneResponse, *, index: int | None = None) -> list[Record]:
    request_id = request_id_of(response)
    records: list[Record] = []
    for name, answer in response.answers.items():
        record: dict[str, object] = {} if index is None else {"index": index}
        record.update({"question": name, "answer": _value(answer)})
        record.update(answer.model_dump(mode="json"))
        record["request_id"] = request_id
        records.append(record)
    return records


# Model and token usage are not part of the rows, so they go to stderr like any other diagnostic.
def usage_line(response: SystemOneResponse) -> str:
    usage = response.usage
    input_tokens = _UNREPORTED if usage.input_tokens is None else usage.input_tokens
    output_tokens = _UNREPORTED if usage.output_tokens is None else usage.output_tokens
    request_id = request_id_of(response) or _UNREPORTED
    return (
        f"model: {response.model} | input tokens: {input_tokens} | output tokens: {output_tokens}"
        f" | request id: {request_id}"
    )


def batch_usage_line(responses: Sequence[SystemOneResponse]) -> str:
    input_tokens = sum(response.usage.input_tokens or 0 for response in responses)
    output_tokens = sum(response.usage.output_tokens or 0 for response in responses)
    return f"answered: {len(responses)} | input tokens: {input_tokens} | output tokens: {output_tokens}"
