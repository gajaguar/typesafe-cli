from dataclasses import dataclass
from typing import Annotated
from typing import Final

import typer

from typesafe_unofficial_cli.runtime.errors import CliError
from typesafe_unofficial_cli.runtime.exit_codes import ExitCode

# The CLI owns authentication, so a header flag cannot replace the credential.
_RESERVED_HEADERS: Final = frozenset({"authorization", "proxy-authorization", "x-api-key", "api-key"})


@dataclass(frozen=True, slots=True)
class RequestOverrides:
    timeout: float | None = None
    max_retries: int | None = None
    headers: dict[str, str] | None = None


# Flags shared by every command that calls the API; a flag wins over the profile's setting.
@dataclass(frozen=True, slots=True)
class RequestOptions:
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", min=0.001, help="Seconds each HTTP operation may take; defaults to the profile's."),
    ] = None
    max_retries: Annotated[
        int | None,
        typer.Option("--max-retries", min=0, help="Retries after the first attempt; 0 disables them."),
    ] = None
    header: Annotated[
        list[str] | None,
        typer.Option("--header", help="Extra request header as 'Name: value'; repeat for several."),
    ] = None

    def overrides(self) -> RequestOverrides:
        return RequestOverrides(
            timeout=self.timeout,
            max_retries=self.max_retries,
            headers=parse_headers(self.header) if self.header else None,
        )


def parse_headers(raw: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in raw:
        name, separator, value = item.partition(":")
        name = name.strip()
        if not separator or not name:
            message = f"Header '{item}' must look like 'Name: value'."
            raise CliError(message, exit_code=ExitCode.USAGE)
        if name.lower() in _RESERVED_HEADERS:
            message = f"The {name} header is managed by the CLI; use `typesafe auth login` instead."
            raise CliError(message, exit_code=ExitCode.USAGE)
        headers[name] = value.strip()
    return headers
