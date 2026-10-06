---
type: guide
title: Updates
description: How each install channel picks up a new version of the skills.
tags: [agents]
---

# Updates

- Claude Code reads the repository when the marketplace is refreshed
  (`/plugin marketplace update typesafe-cli-skills`) and updates the plugin
  when `version` in `plugin.json` changed, so a skills-only change that
  should reach installed users needs a version bump.
- `npx skills` copies the skills from the repository's default branch; run
  `npx skills update` or `npx skills add` again to refresh them.
