from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING
from typing import Final

import typer
from rich.console import Console
from rich.markup import escape
from typesafe_sdk import TypeSafeAPIConnectionError
from typesafe_sdk import TypeSafeAPIError
from typesafe_sdk import TypeSafeAPIResponseValidationError
from typesafe_sdk import TypeSafeAuthenticationError
from typesafe_sdk import TypeSafeBadRequestError
from typesafe_sdk import TypeSafeError
from typesafe_sdk import TypeSafeInternalServerError
from typesafe_sdk import TypeSafeNotFoundError
from typesafe_sdk import TypeSafePermissionDeniedError
from typesafe_sdk import TypeSafeRateLimitError
from typesafe_sdk import TypeSafeUnprocessableEntityError

from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

if TYPE_CHECKING:
    from collections.abc import Callable


class CliError(Exception):
    def __init__(self, message: str, *, exit_code: ExitCode = ExitCode.FAILURE, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.hint = hint


# Ordered most-specific first: the first isinstance match wins. A response that does not match the
# SDK's schema is an upstream fault, so it exits like an unavailable service.
_SDK_EXIT_CODES: Final[tuple[tuple[type[TypeSafeError], ExitCode], ...]] = (
    (TypeSafeAPIResponseValidationError, ExitCode.UNAVAILABLE),
    (TypeSafeAuthenticationError, ExitCode.AUTHENTICATION),
    (TypeSafePermissionDeniedError, ExitCode.FORBIDDEN),
    (TypeSafeNotFoundError, ExitCode.NOT_FOUND),
    (TypeSafeBadRequestError, ExitCode.VALIDATION),
    (TypeSafeUnprocessableEntityError, ExitCode.VALIDATION),
    (TypeSafeRateLimitError, ExitCode.RATE_LIMITED),
    (TypeSafeInternalServerError, ExitCode.UNAVAILABLE),
    (TypeSafeAPIConnectionError, ExitCode.UNAVAILABLE),
    (TypeSafeAPIError, ExitCode.FAILURE),
    (TypeSafeError, ExitCode.CONFIGURATION),
)

_SDK_HINTS: Final[dict[ExitCode, str]] = {
    ExitCode.AUTHENTICATION: "Run `typesafe auth login` to store a valid API key for this profile's provider.",
    ExitCode.RATE_LIMITED: "The provider's rate limit was reached after retries; try again shortly.",
}


def exit_code_for(error: TypeSafeError) -> ExitCode:
    for error_type, exit_code in _SDK_EXIT_CODES:
        if isinstance(error, error_type):
            return exit_code
    return ExitCode.FAILURE


def report(message: str, hint: str | None = None) -> None:
    console = Console(stderr=True, highlight=False)
    console.print(f"[bold red]error:[/] {escape(message)}")
    if hint:
        console.print(f"[dim]hint:[/] {escape(hint)}")


def handle_errors[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except CliError as error:
            report(error.message, error.hint)
            raise typer.Exit(error.exit_code) from error
        except TypeSafeError as error:
            exit_code = exit_code_for(error)
            report(str(error) or type(error).__name__, _SDK_HINTS.get(exit_code))
            raise typer.Exit(exit_code) from error

    return wrapper
