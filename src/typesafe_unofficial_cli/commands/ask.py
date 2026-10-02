from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Final
from typing import cast

import typer

from typesafe_unofficial_cli.output.columns import ANSWERS
from typesafe_unofficial_cli.output.columns import ANSWERS_BATCH
from typesafe_unofficial_cli.output.renderer import Dataset
from typesafe_unofficial_cli.runtime.context import get_app_context
from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.errors import exit_code_for
from typesafe_unofficial_cli.runtime.errors import handle_errors
from typesafe_unofficial_cli.runtime.errors import report
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode
from typesafe_unofficial_cli.runtime.params import options_from
from typesafe_unofficial_cli.runtime.request_options import RequestOptions
from typesafe_unofficial_cli.services.answers import answer_records
from typesafe_unofficial_cli.services.answers import batch_usage_line
from typesafe_unofficial_cli.services.answers import usage_line
from typesafe_unofficial_cli.services.batch import BatchRequest
from typesafe_unofficial_cli.services.batch import run_batch
from typesafe_unofficial_cli.services.inputs import STDIN_MARKER
from typesafe_unofficial_cli.services.inputs import StateFormat
from typesafe_unofficial_cli.services.inputs import read_extra_body
from typesafe_unofficial_cli.services.inputs import read_questions
from typesafe_unofficial_cli.services.inputs import read_state
from typesafe_unofficial_cli.services.inputs import read_states
from typesafe_unofficial_cli.services.question_flags import build_questions

if TYPE_CHECKING:
    from typesafe_sdk import JSONValue
    from typesafe_sdk import QuestionModel
    from typesafe_sdk import TypeSafeError

    from typesafe_unofficial_cli.runtime.context import AppContext
    from typesafe_unofficial_cli.runtime.request_options import RequestOverrides

APP: Final = typer.Typer()


@dataclass(frozen=True, slots=True)
class _AskOptions(RequestOptions):
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
    noul: Annotated[
        list[str] | None,
        typer.Option("--noul", help="Yes/no question as 'name=instructions'; repeat for several."),
    ] = None
    choice: Annotated[
        list[str] | None,
        typer.Option("--choice", help="Choice question as 'name=instructions'; add labels with --criterion."),
    ] = None
    score: Annotated[
        list[str] | None,
        typer.Option("--score", help="Score question as 'name=instructions'; add ordered levels with --criterion."),
    ] = None
    criterion: Annotated[
        list[str] | None,
        typer.Option(
            "--criterion",
            help="Criterion of a flag-defined question as 'name=label[:description]'; repeat, in order for score.",
        ),
    ] = None
    states_file: Annotated[
        Path | None,
        typer.Option(
            "--states-file",
            help="Batch mode: one JSON state (string, object or array) per line; `-` reads standard input.",
        ),
    ] = None
    concurrency: Annotated[
        int, typer.Option("--concurrency", min=1, help="Batch mode: requests in flight at once.")
    ] = 4
    extra_body: Annotated[
        Path | None,
        typer.Option("--extra-body", help="JSON object of extra top-level request fields; `-` reads standard input."),
    ] = None
    model: Annotated[
        str | None, typer.Option("--model", help="Model name; defaults to the profile's, else jev-latest.")
    ] = None


@APP.command(help="Answer named questions (noul, choice, score) about a state with a System One model.")
@handle_errors
@options_from(_AskOptions)
def ask(ctx: typer.Context, options: _AskOptions) -> None:
    if options.questions_file is None and not (options.noul or options.choice or options.score):
        message = "Pass --questions-file or at least one of --noul, --choice and --score."
        raise CliError(message, exit_code=ExitCode.USAGE)
    stdin_sources = [
        flag
        for flag, source in (
            ("--state-file", options.state_file),
            ("--states-file", options.states_file),
            ("--questions-file", options.questions_file),
            ("--extra-body", options.extra_body),
        )
        if str(source) == STDIN_MARKER
    ]
    if len(stdin_sources) > 1:
        message = f"Only one of {', '.join(stdin_sources)} can read standard input."
        raise CliError(message, exit_code=ExitCode.USAGE)
    if options.states_file is not None and (options.state is not None or options.state_file is not None):
        message = "--states-file cannot be combined with --state or --state-file."
        raise CliError(message, exit_code=ExitCode.USAGE)
    app_context = get_app_context(ctx)
    overrides = options.overrides()
    # A question defined by flag replaces a file question of the same name.
    questions = {} if options.questions_file is None else read_questions(options.questions_file)
    questions |= build_questions(
        noul=options.noul or [],
        choice=options.choice or [],
        score=options.score or [],
        criterion=options.criterion or [],
    )
    extra_body = None if options.extra_body is None else read_extra_body(options.extra_body)
    if options.states_file is not None:
        _ask_batch(app_context, options, overrides, questions, extra_body)
        return
    content = read_state(text=options.state, file=options.state_file, state_format=options.state_format)
    response = app_context.client(overrides).system_one(content, questions, model=options.model, extra_body=extra_body)
    app_context.notify(usage_line(response))
    app_context.render(Dataset(records=answer_records(response), columns=ANSWERS, id_key="question"))


# Answers are rendered first, then each failed state is reported and the first failure sets the exit code.
def _ask_batch(
    app_context: AppContext,
    options: _AskOptions,
    overrides: RequestOverrides,
    questions: dict[str, QuestionModel],
    extra_body: dict[str, JSONValue | None] | None,
) -> None:
    request = BatchRequest(
        states=read_states(cast("Path", options.states_file)),
        questions=questions,
        model=options.model,
        extra_body=extra_body,
        concurrency=options.concurrency,
    )
    items = run_batch(app_context.async_client(overrides), request)
    answered = [item.response for item in items if item.response is not None]
    records = [
        record
        for item in items
        if item.response is not None
        for record in answer_records(item.response, index=item.index)
    ]
    app_context.notify(batch_usage_line(answered))
    app_context.render(Dataset(records=records, columns=ANSWERS_BATCH, id_key="question"))
    failures = [item for item in items if item.error is not None]
    for item in failures:
        report(f"state {item.index}: {item.error}")
    if failures:
        message = f"{len(failures)} of {len(items)} states failed."
        raise CliError(message, exit_code=exit_code_for(cast("TypeSafeError", failures[0].error)))
