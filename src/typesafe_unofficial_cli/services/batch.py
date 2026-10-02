from __future__ import annotations

import asyncio
from dataclasses import dataclass
from itertools import starmap
from typing import TYPE_CHECKING

from typesafe_sdk import TypeSafeError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

    from typesafe_sdk import AsyncTypeSafeClient
    from typesafe_sdk import JSONContent
    from typesafe_sdk import JSONValue
    from typesafe_sdk import QuestionModel
    from typesafe_sdk import SystemOneResponse


@dataclass(frozen=True, slots=True)
class BatchItem:
    index: int
    response: SystemOneResponse | None = None
    error: TypeSafeError | None = None


@dataclass(frozen=True, slots=True)
class BatchRequest:
    states: Sequence[JSONContent]
    questions: Mapping[str, QuestionModel]
    model: str | None
    extra_body: Mapping[str, JSONValue | None] | None
    concurrency: int


# Items come back in input order whatever order they finish in; a failed state is kept as an error
# so the others still answer.
async def _run(client: AsyncTypeSafeClient, request: BatchRequest) -> list[BatchItem]:
    gate = asyncio.Semaphore(request.concurrency)

    async def one(index: int, state: JSONContent) -> BatchItem:
        async with gate:
            try:
                response = await client.system_one(
                    state, request.questions, model=request.model, extra_body=request.extra_body
                )
            except TypeSafeError as error:
                return BatchItem(index=index, error=error)
            return BatchItem(index=index, response=response)

    async with client:
        return list(await asyncio.gather(*starmap(one, enumerate(request.states))))


def run_batch(client: AsyncTypeSafeClient, request: BatchRequest) -> list[BatchItem]:
    return asyncio.run(_run(client, request))
