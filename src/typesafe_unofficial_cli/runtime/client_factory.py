from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Final

from typesafe_sdk import TypeSafeClient

if TYPE_CHECKING:
    from typesafe_unofficial_cli.auth.credentials import Credential


# Per-invocation bundle so the client factory does not grow a long positional argument list every
# time a new flag appears. `model=None` lets the SDK apply TYPESAFE_DEFAULT_MODEL, then its default.
@dataclass(frozen=True, slots=True)
class ClientRequest:
    credential: Credential
    base_url: str
    model: str | None = None
    verbose: bool = False


type ClientFactory = Callable[[ClientRequest], TypeSafeClient]  # pylint: disable=gajaguar-module-const-naming

_SDK_LOGGER: Final = "typesafe_sdk"


# The SDK logs through the standard library and redacts credential headers, so verbose mode only has
# to route that logger to stderr.
def _enable_verbose_logging() -> None:
    logger = logging.getLogger(_SDK_LOGGER)
    logger.setLevel(logging.DEBUG)
    if not any(
        isinstance(handler, logging.StreamHandler) and handler.stream is sys.stderr for handler in logger.handlers
    ):
        logger.addHandler(logging.StreamHandler(sys.stderr))


def create_sdk_client(request: ClientRequest) -> TypeSafeClient:
    if request.verbose:
        _enable_verbose_logging()
    return TypeSafeClient(api_key=request.credential.api_key, base_url=request.base_url, model=request.model)
