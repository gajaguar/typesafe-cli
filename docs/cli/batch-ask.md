---
type: reference
title: Batch ask
description: How `typesafe ask --states-file` orders its output, reports failed states and chooses its exit code.
tags: [cli, ask]
---

# Batch ask

`typesafe ask --states-file states.jsonl --questions-file questions.json`
asks the same questions about many states, sending up to `--concurrency`
requests at once (default 4).

## Input

One JSON value per line: a string, an object or an array. Blank lines are
skipped, and a state's `index` counts the non-blank lines from zero.

`--states-file` cannot be combined with `--state` or `--state-file`.

## Output

- Every record carries the `index` of its state, so the table, JSON and CSV
  formats all keep rows grouped by state in input order, however the requests
  finish.
- Token totals and the number of answered states go to stderr.

## Partial failure

A failed state does not stop the others. The answers that arrived are rendered
first, each failure is then reported on stderr as `state <index>: <message>`,
and the exit code is the one the first failed state maps to (see
`runtime/exit_codes.py`). A batch with at least one failure never exits `0`.
