from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from typesafe_unofficial_cli.auth.credentials import ApiKeyCredential
from typesafe_unofficial_cli.runtime.client_factory import ClientRequest
from typesafe_unofficial_cli.runtime.client_factory import create_async_sdk_client
from typesafe_unofficial_cli.runtime.client_factory import create_sdk_client

if TYPE_CHECKING:
    import pytest


def test_factory_builds_a_client_for_the_requested_host(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)
    request = ClientRequest(credential=ApiKeyCredential(api_key="k"), base_url="https://example.com", model="jev-1.13")
    # Act
    with create_sdk_client(request) as client:
        config = client._config  # ruff: ignore[private-member-access]
    # Assert
    assert (config.base_url, config.default_model) == ("https://example.com", "jev-1.13")


def test_ambient_base_url_variable_never_overrides_the_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("TYPESAFE_BASE_URL", "https://elsewhere.example.com")
    request = ClientRequest(credential=ApiKeyCredential(api_key="k"), base_url="https://api.typesafe.ai")
    # Act
    with create_sdk_client(request) as client:
        config = client._config  # ruff: ignore[private-member-access]
    # Assert
    assert config.base_url == "https://api.typesafe.ai"


def test_verbose_routes_the_sdk_logger_to_stderr_once() -> None:
    # Arrange
    logger = logging.getLogger("typesafe_sdk")
    handlers_before = list(logger.handlers)
    request = ClientRequest(credential=ApiKeyCredential(api_key="k"), base_url="https://example.com", verbose=True)
    # Act
    create_sdk_client(request).close()
    create_sdk_client(request).close()
    added = [handler for handler in logger.handlers if handler not in handlers_before]
    for handler in added:
        logger.removeHandler(handler)
    # Assert
    assert len(added) == 1
    assert logger.level == logging.DEBUG


def test_factory_applies_timeout_retries_and_headers() -> None:
    # Arrange
    request = ClientRequest(
        credential=ApiKeyCredential(api_key="k"),
        base_url="https://example.com",
        timeout=7,
        max_retries=0,
        headers={"X-Trace": "t"},
    )
    # Act
    client = create_sdk_client(request)
    async_client = create_async_sdk_client(request)
    configs = [client._config, async_client._config]  # ruff: ignore[private-member-access]
    client.close()
    # Assert
    assert [(config.timeout, config.default_headers["X-Trace"]) for config in configs] == [(7, "t")] * 2
