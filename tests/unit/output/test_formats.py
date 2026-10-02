from __future__ import annotations

import io
import json
from typing import Final

import pytest
from rich.console import Console

from typesafe_unofficial_cli.config.settings import OutputFormat
from typesafe_unofficial_cli.output.registry import create_renderer
from typesafe_unofficial_cli.output.renderer import Column
from typesafe_unofficial_cli.output.renderer import RenderTarget
from typesafe_unofficial_cli.output.renderer import many
from typesafe_unofficial_cli.output.renderer import single
from typesafe_unofficial_cli.output.renderer import to_record

COLUMNS: Final = (Column("id", "ID"), Column("nested.value", "Value"), Column("flag", "Flag"))
ROWS: Final = [
    {"id": "a", "nested": {"value": 1}, "flag": True},
    {"id": "b", "nested": None, "flag": None},
]


def _render(output: OutputFormat, dataset_rows: list[dict[str, object]], *, one: bool = False) -> str:
    stream = io.StringIO()
    target = RenderTarget(console=Console(file=stream, width=120, highlight=False), stream=stream)
    dataset = single(dataset_rows[0], COLUMNS) if one else many(dataset_rows, COLUMNS)
    create_renderer(output, target).render(dataset)
    return stream.getvalue()


def test_json_renders_a_list_of_records() -> None:
    # Arrange
    output = OutputFormat.JSON
    # Act
    rendered = _render(output, ROWS)
    # Assert
    assert json.loads(rendered) == ROWS


def test_json_renders_a_single_record_as_an_object() -> None:
    # Arrange
    output = OutputFormat.JSON
    first, *_ = ROWS
    # Act
    rendered = _render(output, ROWS, one=True)
    # Assert
    assert json.loads(rendered) == first


def test_jsonl_renders_one_record_per_line() -> None:
    # Arrange
    output = OutputFormat.JSONL
    # Act
    rendered = _render(output, ROWS)
    # Assert
    assert [json.loads(line) for line in rendered.splitlines()] == ROWS


def test_csv_follows_the_column_specs_and_blanks_none() -> None:
    # Arrange
    output = OutputFormat.CSV
    # Act
    rendered = _render(output, ROWS)
    # Assert
    assert rendered.splitlines() == ["ID,Value,Flag", "a,1,yes", "b,,"]


def test_id_prints_one_identifier_per_line() -> None:
    # Arrange
    output = OutputFormat.ID
    # Act
    rendered = _render(output, ROWS)
    # Assert
    assert rendered == "a\nb\n"


def test_table_lists_headers_and_values() -> None:
    # Arrange
    output = OutputFormat.TABLE
    # Act
    rendered = _render(output, ROWS)
    # Assert
    assert "ID" in rendered
    assert "yes" in rendered


def test_table_single_record_shows_header_value_pairs() -> None:
    # Arrange
    output = OutputFormat.TABLE
    # Act
    rendered = _render(output, ROWS, one=True)
    # Assert
    assert "Flag" in rendered
    assert "yes" in rendered


def test_to_record_rejects_unknown_types() -> None:
    # Arrange
    item = 42
    # Act
    with pytest.raises(TypeError, match="Cannot coerce int") as error:
        to_record(item)
    # Assert
    assert error.type is TypeError
