from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Final
from urllib.parse import urlsplit

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator

from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.providers import spec_for

DEFAULT_PROFILE: Final = "default"
_LOOPBACK_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    ID = "id"


class Profile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Provider = Provider.TYPESAFE
    base_url: str | None = None
    model: str | None = None
    timeout: float | None = None
    max_retries: int | None = None

    @field_validator("timeout")
    @classmethod
    def _require_positive_timeout(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value <= 0):
            message = "timeout must be a positive, finite number of seconds"
            raise ValueError(message)
        return value

    @field_validator("max_retries")
    @classmethod
    def _require_non_negative_retries(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            message = "max_retries must be zero or greater"
            raise ValueError(message)
        return value

    # The API key travels in the Authorization header, so a plain-HTTP host is only accepted on loopback.
    @field_validator("base_url")
    @classmethod
    def _require_secure_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value)
        if parts.scheme == "https" and parts.hostname:
            return value.rstrip("/")
        if parts.scheme == "http" and parts.hostname in _LOOPBACK_HOSTS:
            return value.rstrip("/")
        message = "base_url must be an https URL (http is only allowed for localhost)"
        raise ValueError(message)

    def effective_base_url(self) -> str:
        return self.base_url or spec_for(self.provider).base_url


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    default_profile: str = DEFAULT_PROFILE
    output: OutputFormat | None = None
    profiles: dict[str, Profile] = {}

    def with_profile(self, name: str, profile: Profile) -> Settings:
        return self.model_copy(update={"profiles": {**self.profiles, name: profile}})

    def without_profile(self, name: str) -> Settings:
        remaining = {key: value for key, value in self.profiles.items() if key != name}
        return self.model_copy(update={"profiles": remaining})


# Flag and environment values arrive already merged by Typer (flag wins over envvar).
@dataclass(frozen=True, slots=True)
class GlobalOptions:
    profile: str | None = None
    output: OutputFormat | None = None
    verbose: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedOptions:
    profile_name: str
    profile: Profile
    output: OutputFormat
    verbose: bool


def resolve_options(options: GlobalOptions, settings: Settings, *, is_tty: bool) -> ResolvedOptions:
    profile_name = options.profile or settings.default_profile
    profile = settings.profiles.get(profile_name, Profile())
    # Humans get tables; pipes get machine-readable JSON unless something explicit says otherwise.
    fallback_output = OutputFormat.TABLE if is_tty else OutputFormat.JSON
    return ResolvedOptions(
        profile_name=profile_name,
        profile=profile,
        output=options.output or settings.output or fallback_output,
        verbose=options.verbose,
    )
