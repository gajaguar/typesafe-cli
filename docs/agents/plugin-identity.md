---
type: reference
title: Plugin identity
description: The marketplace and plugin names, the repository layout, and why plugin.json carries the only copy of the plugin version.
tags: [agents, versioning]
---

# Plugin identity

- Marketplace: `typesafe-cli-skills`, in `.claude-plugin/marketplace.json`.
- Plugin: `typesafe-cli`, in `.claude-plugin/plugin.json`, with its skills
  auto-discovered from `skills/<skill>/SKILL.md`. It ships no MCP server and
  no hooks.
- Skills: `typesafe-cli` (auth, profiles, config, models, exit codes) and
  `typesafe-ask` (the `ask` command and the questions file).

The plugin version lives only in `plugin.json`; the marketplace entry omits
it so there is one copy to keep aligned. `make plugin-version-check`, part of
`make check`, fails when it differs from `project.version` in
`pyproject.toml`. The bump commit sets both, as
[versioning](../conventions/versioning.md) says.

`make skills-validate` validates every `skills/*/SKILL.md` against the
[Agent Skills specification](https://agentskills.io/specification).
