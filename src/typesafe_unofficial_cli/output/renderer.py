from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Protocol

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from typing import TextIO

    from rich.console import Console

type Record = Mapping[str, object]  # pylint: disable=gajaguar-module-const-naming


@dataclass(frozen=True, slots=True)
class Column:
    key: str
    header: str

    # Keys may be dotted paths into nested API objects, e.g. "timeInterval.duration".
    def value(self, record: Record) -> object:
        current: object = record
        for part in self.key.split("."):
            if not isinstance(current, Mapping):
                return None
            current = current.get(part)
        return current


@dataclass(frozen=True, slots=True)
class Dataset:
    records: Sequence[Record]
    columns: Sequence[Column]
    single: bool = False
    # Field printed by the `id` format; resources without an `id` name another one.
    id_key: str = "id"


@dataclass(frozen=True, slots=True)
class RenderTarget:
    console: Console
    stream: TextIO = field(repr=False)


class Renderer(Protocol):
    def render(self, dataset: Dataset) -> None: ...


# JSON output keeps the API's own snake_case field names so it lines up with the TypeSafe docs.
def to_record(item: BaseModel | Record | object) -> Record:
    if isinstance(item, BaseModel):
        return item.model_dump(mode="json")
    if isinstance(item, Mapping):
        return item
    message = f"Cannot coerce {type(item).__name__} to a renderer record."
    raise TypeError(message)


def many(items: Iterable[BaseModel | Record], columns: Sequence[Column], *, id_key: str = "id") -> Dataset:
    return Dataset(records=[to_record(item) for item in items], columns=columns, id_key=id_key)


def single(item: BaseModel | Record, columns: Sequence[Column]) -> Dataset:
    return Dataset(records=[to_record(item)], columns=columns, single=True)
