from typing import Final

from typesafe_unofficial_cli.output.renderer import Column

AUTH_STATUS: Final = (
    Column("profile", "Profile"),
    Column("provider", "Provider"),
    Column("base_url", "Base URL"),
    Column("model", "Model"),
    Column("source", "Credential source"),
    Column("api_key", "API key"),
)

PROFILES: Final = (
    Column("name", "Profile"),
    Column("default", "Default"),
    Column("provider", "Provider"),
    Column("base_url", "Base URL"),
    Column("model", "Model"),
)

MODELS: Final = (
    Column("name", "Name"),
    Column("release_date", "Released"),
    Column("description", "Description"),
)

ANSWERS: Final = (
    Column("question", "Question"),
    Column("type", "Type"),
    Column("answer", "Answer"),
    Column("confidence", "Confidence"),
)
