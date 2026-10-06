# Questions file

One object keyed by question name. Each question has `type` (`noul`,
`choice` or `score`) and `instructions`.

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
- `choice`: `criteria` required, object of label to description.
- `score`: `criteria` required, list of level descriptions from zero.

## JSON or YAML

- `.yaml` / `.yml` is YAML, whatever the case.
- Standard input (`-`) is tried as JSON, then as YAML.
- Any other file is JSON; YAML inside a `.json` file is an error.
- `--extra-body` follows the same rules. `--states-file` is always JSONL.

## YAML rules

- Only `true` and `false` are booleans; `yes`, `no`, `on`, `off` stay text.
- Dates stay text.
- An unquoted `true:` or `false:` key of a noul question is read as the text
  `"true"` / `"false"`.
- Every other key must be text: quote numeric or boolean question names and
  labels, or the command exits with code 2.

## Question flags

`--noul`, `--choice`, `--score` take `name=instructions`; `--criterion
name=value` adds criteria to the question of that name.

- `noul` criterion: `true|false[:description]`.
- `choice` criterion: `label[:description]` (splits on the first colon).
- `score` criterion: the whole text is one level; flag order is the level order.

Errors that exit 2 without a request: a flag without `name=` or instructions,
a name defined twice among flags, a `--criterion` for an undefined name, a
choice or score without criteria, a noul label other than `true`/`false`, a
repeated or empty label.
