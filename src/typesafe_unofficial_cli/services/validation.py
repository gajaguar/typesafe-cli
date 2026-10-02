from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

from typesafe_sdk import Noul

from typesafe_unofficial_cli.config.providers import Provider

if TYPE_CHECKING:
    from typesafe_sdk import TypeSafeClient

_PROBE_STATE: Final = "ping"


# TypeSafe lists models only to an authenticated key, which costs nothing. OpenRouter's model list is
# public and the SDK cannot parse it, so a real key check needs one minimal System One request.
def verify_key(client: TypeSafeClient, provider: Provider) -> None:
    if provider is Provider.TYPESAFE:
        client.models.list()
        return
    client.system_one(state=_PROBE_STATE, questions={"probe": Noul(instructions="Is this a short test message?")})
