from __future__ import annotations

import pytest
from pydantic import ValidationError

from typesafe_unofficial_cli.config.paths import CONFIG_DIR_ENV_VAR
from typesafe_unofficial_cli.config.paths import config_dir
from typesafe_unofficial_cli.config.paths import credentials_file
from typesafe_unofficial_cli.config.paths import settings_file
from typesafe_unofficial_cli.config.providers import Provider
from typesafe_unofficial_cli.config.settings import GlobalOptions
from typesafe_unofficial_cli.config.settings import OutputFormat
from typesafe_unofficial_cli.config.settings import Profile
from typesafe_unofficial_cli.config.settings import Settings
from typesafe_unofficial_cli.config.settings import resolve_options


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://proxy.example.com/", "https://proxy.example.com"),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://127.0.0.1:9000/", "http://127.0.0.1:9000"),
        (None, None),
    ],
)
def test_profile_accepts_secure_or_loopback_urls(value: str | None, expected: str | None) -> None:
    # Arrange
    # Act
    profile = Profile(base_url=value)
    # Assert
    assert profile.base_url == expected


@pytest.mark.parametrize("value", ["http://example.com", "ftp://example.com", "not a url", "https://"])
def test_profile_rejects_insecure_or_malformed_urls(value: str) -> None:
    # Arrange
    raw = {"base_url": value}
    # Act
    with pytest.raises(ValidationError) as error:
        Profile.model_validate(raw)
    # Assert
    assert error.type is ValidationError


def test_profile_rejects_unknown_keys() -> None:
    # Arrange
    raw = {"provider": "typesafe", "typo": 1}
    # Act
    with pytest.raises(ValidationError) as error:
        Profile.model_validate(raw)
    # Assert
    assert error.type is ValidationError


def test_effective_base_url_prefers_the_override() -> None:
    # Arrange
    profile = Profile(provider=Provider.OPENROUTER, base_url="https://proxy.example.com")
    # Act
    effective = profile.effective_base_url()
    # Assert
    assert effective == "https://proxy.example.com"


def test_resolve_options_precedence() -> None:
    # Arrange
    settings = Settings(
        default_profile="b", output=OutputFormat.CSV, profiles={"a": Profile(), "b": Profile(model="m")}
    )
    # Act
    from_settings = resolve_options(GlobalOptions(), settings, is_tty=True)
    from_flags = resolve_options(GlobalOptions(profile="a", output=OutputFormat.ID), settings, is_tty=True)
    # Assert
    assert (from_settings.profile_name, from_settings.profile.model, from_settings.output) == (
        "b",
        "m",
        OutputFormat.CSV,
    )
    assert (from_flags.profile_name, from_flags.output) == ("a", OutputFormat.ID)


@pytest.mark.parametrize(("is_tty", "expected"), [(True, OutputFormat.TABLE), (False, OutputFormat.JSON)])
def test_resolve_options_output_fallback_depends_on_tty(is_tty: bool, expected: OutputFormat) -> None:
    # Arrange
    options = GlobalOptions()
    # Act
    resolved = resolve_options(options, Settings(), is_tty=is_tty)
    # Assert
    assert resolved.output is expected


def test_config_dir_honors_the_override(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    # Arrange
    monkeypatch.setenv(CONFIG_DIR_ENV_VAR, str(tmp_path))
    # Act
    directory = config_dir()
    # Assert
    assert directory == tmp_path
    assert settings_file() == directory / "config.toml"
    assert credentials_file() == directory / "credentials.toml"


def test_config_dir_defaults_to_the_platform_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.delenv(CONFIG_DIR_ENV_VAR, raising=False)
    # Act
    directory = config_dir()
    # Assert
    assert directory.name == "typesafe-cli"
