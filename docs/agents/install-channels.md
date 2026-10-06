---
type: guide
title: Install channels
description: The two ways to install the skills, the Claude Code plugin marketplace and npx skills.
tags: [agents]
---

# Install channels

Claude Code:

```text
/plugin marketplace add gajaguar/typesafe-cli
/plugin install typesafe-cli@typesafe-cli-skills
```

Any Agent Skills-compatible agent:

```bash
npx skills add gajaguar/typesafe-cli
npx skills add gajaguar/typesafe-cli -a opencode -y
```

The skills only install context. The `typesafe` command itself comes from
`uv tool install typesafe-unofficial-cli` (Python 3.14+), and a key must be
stored with `typesafe auth login`.
