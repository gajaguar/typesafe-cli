from __future__ import annotations

import json
from enum import StrEnum
from typing import Final

import yaml


class TemplateFormat(StrEnum):
    JSON = "json"
    YAML = "yaml"


# One question of each kind; `instructions` is always present because OpenRouter answers 400 without it.
QUESTIONS_TEMPLATE: Final = {
    "billing": {
        "type": "noul",
        "instructions": "Is the message about billing?",
        "criteria": {"true": "It mentions a charge, an invoice or a refund.", "false": "It is about something else."},
    },
    "tone": {
        "type": "choice",
        "instructions": "What is the tone of the message?",
        "criteria": {"calm": "Neutral or polite.", "angry": "Hostile or upset."},
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is the message?",
        "criteria": ["Not urgent.", "Should be answered soon.", "Needs an answer right away."],
    },
}


def render_template(template_format: TemplateFormat) -> str:
    if template_format is TemplateFormat.JSON:
        return json.dumps(QUESTIONS_TEMPLATE, indent=2)
    return yaml.safe_dump(QUESTIONS_TEMPLATE, sort_keys=False, allow_unicode=True).rstrip("\n")
