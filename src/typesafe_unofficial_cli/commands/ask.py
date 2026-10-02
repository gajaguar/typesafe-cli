from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from typing import Final

import typer

from typesafe_unofficial_cli.output.columns import ANSWERS
from typesafe_unofficial_cli.output.renderer import Dataset
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode
from typesafe_unofficial_cli.runtime.params import options_from
from typesafe_unofficial_cli.services.answers import answer_records
from typesafe_unofficial_cli.services.answers import usage_line
from typesafe_unofficial_cli.services.inputs import STDIN_MARKER
from typesafe_unofficial_cli.services.inputs import StateFormat
from typesafe_unofficial_cli.services.inputs import read_questions
from typesafe_unofficial_cli.services.inputs import read_state

APP: Final = typer.Typer()


@dataclass(frozen=True, slots=True)
class _AskOptions:
    state: Annotated[str | None, typer.Option("--state", help="The text to evaluate.")] = None
    state_file: Annotated[
        Path | None,
        typer.Option("--state-file", help="Read the state from a file; `-` reads standard input."),
    ] = None
    state_format: Annotated[
        StateFormat,
        typer.Option(
            "--state-format", case_sensitive=False, help="Parse the state as plain text or as a JSON object/array."
        ),
    ] = StateFormat.TEXT
    questions_file: Annotated[
        Path | None,
        typer.Option(
            "--questions-file",
            help='JSON object of named questions, each {"type": "noul|choice|score", ...}; `-` reads standard input.',
        ),
    ] = None
    model: Annotated[
        str | None, typer.Option("--model", help="Model name; defaults to the profile's, else jev-latest.")
    ] = None


@APP.command(help="Answer named questions (noul, choice, score) about a state with a System One model.")
@handle_errors
@options_from(_AskOptions)
def ask(ctx: typer.Context, options: _AskOptions) -> None:
    if options.questions_file is None:
        message = "--questions-file is required."
        raise CliError(message, exit_code=ExitCode.USAGE)
    if str(options.state_file) == STDIN_MARKER and str(options.questions_file) == STDIN_MARKER:
        message = "Only one of --state-file and --questions-file can read standard input."
        raise CliError(message, exit_code=ExitCode.USAGE)
    app_context = get_app_context(ctx)
    content = read_state(text=options.state, file=options.state_file, state_format=options.state_format)
    questions = read_questions(options.questions_file)
    response = app_context.client().system_one(content, questions, model=options.model)
    app_context.notify(usage_line(response))
    app_context.render(Dataset(records=answer_records(response), columns=ANSWERS, id_key="question"))
