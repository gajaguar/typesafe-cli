---
name: typesafe-cli
description: Use the `typesafe` command-line tool (typesafe-unofficial-cli) for TypeSafe AI and OpenRouter System One models - install it, log in, switch profiles or providers, edit config, list models, pick an output format and read exit codes. Use when the user says "typesafe auth login", "switch the profile to OpenRouter", "set the typesafe model", "list typesafe models", "typesafe exit code" or "typesafe config".
license: MIT
compatibility: Needs the typesafe-unofficial-cli package (Python 3.14+) and an API key stored with `typesafe auth login` or set in an environment variable.
---

# typesafe CLI

`typesafe` is an unofficial CLI for TypeSafe AI System One models, served by
TypeSafe or OpenRouter. To ask questions about a text, use the `typesafe-ask`
skill; this one covers everything around it.

## Requirements

- Install: `uv tool install typesafe-unofficial-cli` (Python 3.14 or newer).
- A key must exist before any request: run `typesafe auth login`, or set
  `TYPESAFE_API_KEY` / `OPENROUTER_API_KEY`.
- Check the real surface with `typesafe --help` and `typesafe <command> --help`
  before using a flag that is not listed here.

## Rules

- Global options go **before** the command:
  `typesafe -p openrouter -o json ask ...`, never `typesafe ask -o json`.
- Never pass the API key as a flag or argument. Use the hidden prompt of
  `auth login`, `auth login --with-token` (reads standard input), or the
  environment variable.
- Prefer `-o json` (or `jsonl`) when the output will be parsed.
- Do not run `auth token` unless the user asks: it prints the raw key.

## Global options

- `-p`, `--profile`: profile to use (env `TYPESAFE_CLI_PROFILE`).
- `-o`, `--output`: `table`, `json`, `jsonl`, `csv` or `id` (env
  `TYPESAFE_CLI_OUTPUT`).
- `-v`, `--verbose`: log the SDK's HTTP activity to stderr.

## Commands

- `auth login [--provider typesafe|openrouter] [--base-url URL] [--with-token]
  [--insecure-storage] [--skip-validation]`: validate and store a key for the
  selected profile.
- `auth status [--check]`: show the active credential; `--check` validates it
  with the provider.
- `auth logout`: remove the stored credential and profile.
- `auth token`: print the raw key.
- `config path|list|use NAME|set KEY VALUE|get KEY|unset KEY`: profile keys
  are `provider`, `base_url`, `model`, `timeout`, `max_retries`; `output` is
  global.
- `models list [--timeout] [--max-retries] [--header 'Name: value']`:
  TypeSafe only.

Example, a second profile on OpenRouter:

```bash
typesafe -p openrouter auth login --provider openrouter
typesafe config use openrouter
typesafe config set model jev-latest
```

## References

- [Profiles and providers](references/profiles.md)
- [Exit codes](references/exit-codes.md)
