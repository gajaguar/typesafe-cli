---
type: decision
title: Public contract
description: What 1.0.0 freezes (commands, flags, output fields, exit codes, settings keys, environment variables) and what stays free to change.
tags: [release, versioning, contract]
status: stable
---

# Public contract

From `1.0.0` a breaking change to anything listed under *Frozen* needs a
major bump, as [versioning](versioning.md) defines.

## Frozen

- **Commands and flags**: the command tree, option names and positional
  arguments. `tests/unit/test_contract.py` holds the snapshot.
- **Record fields**: the field names of `ask`, `models list`, `auth status`
  and `config list` in the `json`, `jsonl`, `csv` and `id` formats, and the
  `id` key each format prints. The same test checks them.
- **Exit codes**: the numeric values in `runtime/exit_codes.py`.
- **Settings keys**: the keys of `config.toml` and of `config set|get|unset`.
- **Environment variables**: `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`,
  `TYPESAFE_CLI_PROFILE`, `TYPESAFE_CLI_OUTPUT` and
  `TYPESAFE_CLI_CONFIG_DIR`.

## Free to change

- The `table` format and any text on stderr, including status, usage and
  error messages.
- Help texts.
- New commands, options, record fields and settings keys: adding is a minor
  bump, only removing or renaming breaks the contract.
- The `typesafe-sdk` version range, unless it changes a frozen item.
