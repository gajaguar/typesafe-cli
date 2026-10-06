---
type: reference
title: Questions file
description: The shape of the file `typesafe ask --questions-file` reads, how JSON and YAML are told apart, the YAML rules that differ from PyYAML's defaults, and `--questions-template`.
tags: [cli, ask]
---

# Questions file

`--questions-file` reads one object keyed by question name. Each question has a
`type` of `noul`, `choice` or `score`, and `instructions`. `--extra-body` reads
its object the same way.

```yaml
billing:
  type: noul
  instructions: Is the message about billing?
tone:
  type: choice
  instructions: What is the tone of the message?
  criteria:
    calm: Neutral or polite.
    angry: Hostile or upset.
urgency:
  type: score
  instructions: How urgent is the message?
  criteria:
    - Not urgent.
    - Needs an answer right away.
```

- `noul`: optional `criteria`, an object with the keys `true` and `false`.
- `choice`: `criteria` is an object of label to description, and is required.
- `score`: `criteria` is a list of level descriptions, from zero, and is
  required.

`instructions` is always required in practice: OpenRouter answers 400 without
it, even though the SDK marks it optional.

## JSON or YAML

- A `.yaml` or `.yml` file is YAML, whatever the case of the extension.
- Standard input (`-`) is parsed as JSON first and as YAML when that fails.
- Any other file is JSON, so a YAML document in a `.json` file is an error.

`--states-file` is JSONL and does not change.

## YAML rules

The YAML loader differs from PyYAML's YAML 1.1 defaults so that the result is
always valid JSON:

- Only `true` and `false` load as booleans. `yes`, `no`, `on` and `off` stay
  text.
- Dates stay text instead of becoming date objects.
- An unquoted `true:` or `false:` key of a noul question is read as the text
  `"true"` or `"false"`.
- Every other key must be text. A number or a boolean used as a question name
  or criterion label exits with the usage code, and the message asks to quote
  it.

## Template

`typesafe ask --questions-template json|yaml` prints a valid file with one
question of each kind and exits 0. It needs no `--state`, no questions file and
no credentials.

```bash
typesafe ask --questions-template yaml > questions.yaml
```
