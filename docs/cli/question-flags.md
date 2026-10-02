---
type: concept
title: Question flags
description: How `typesafe ask` builds questions from `--noul`, `--choice`, `--score` and `--criterion`, and how they combine with `--questions-file`.
tags: [cli, ask]
---

# Question flags

`typesafe ask` can define questions without a file. Each question is one flag,
`name=instructions`; its criteria are separate, repeatable `--criterion` flags
that name the question they belong to.

```bash
typesafe ask --state "The parcel arrived broken." \
  --noul 'billing=Is this about billing?' \
  --choice 'tone=What is the tone?' \
  --criterion tone=calm --criterion 'tone=angry:Hostile or upset' \
  --score 'urgency=How urgent is it?' \
  --criterion urgency=low --criterion urgency=medium --criterion urgency=high
```

## Criteria

- `noul`: optional, `true` or `false`, then `[:description]`.
- `choice`: required, `label[:description]`.
- `score`: required, the description of one level.

A choice or noul value splits on its first colon, so a description may contain
more colons. A score keeps the value whole, colons included, and the order of
the flags is the order of the levels from zero.

## Combining with a file

Flags and `--questions-file` can be used together. A question defined by flag
replaces the file question with the same name; the rest of the file is kept.
`--questions-file` is only required when no `--noul`, `--choice` or `--score`
is given.

## Errors

Each of these exits with the usage code and sends no request: a flag without
`name=` or without instructions, a name defined twice among the flags, a
`--criterion` for a name no flag defines, a choice or score without criteria, a
noul label other than `true` or `false`, and a repeated or empty label.

Instructions are always required here because OpenRouter answers 400 without
them, even though the SDK marks them optional.
