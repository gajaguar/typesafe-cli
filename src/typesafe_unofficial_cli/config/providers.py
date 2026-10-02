from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Provider(StrEnum):
    TYPESAFE = "typesafe"
    OPENROUTER = "openrouter"


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    display_name: str
    base_url: str
    api_key_env_var: str


# Each provider reads its own environment variable. A key is never tried against another provider's
# host, so a TypeSafe key cannot leak to OpenRouter (or the reverse) through a mismatched profile.
SPECS: Final[dict[Provider, ProviderSpec]] = {
    Provider.TYPESAFE: ProviderSpec(
        display_name="TypeSafe",
        base_url="https://api.typesafe.ai",
        api_key_env_var="TYPESAFE_API_KEY",
    ),
    Provider.OPENROUTER: ProviderSpec(
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api",
        api_key_env_var="OPENROUTER_API_KEY",
    ),
}


def spec_for(provider: Provider) -> ProviderSpec:
    return SPECS[provider]
