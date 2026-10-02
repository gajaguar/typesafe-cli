# TypeSafe Unofficial CLI

> **Unofficial.** This project is not affiliated with, endorsed by, or
> supported by TypeSafe AI or OpenRouter. "TypeSafe", "Jev" and
> "OpenRouter" belong to their owners.

Unofficial command-line interface for TypeSafe AI System One models, on
TypeSafe or OpenRouter, built on
[`typesafe-sdk`](https://pypi.org/project/typesafe-sdk/).

## Install

```bash
uv tool install typesafe-unofficial-cli
```

It needs Python 3.14 or newer. To work on the CLI from a checkout, run
`make install`.

## Usage

Log in once per provider profile. The key is read from a hidden prompt:

```bash
typesafe auth login
typesafe -p openrouter auth login --provider openrouter
```

Ask questions about some text. Each question is `noul`, `choice` or
`score`:

```bash
echo '{"billing": {"type": "noul", "instructions": "Is this billing?"}}' \
  > questions.json
typesafe ask --state "I was charged twice." --questions-file questions.json
```

Ask the same questions about many states, one JSON value per line, with
several requests in flight (see [batch ask](docs/cli/batch-ask.md)):

```bash
typesafe ask --states-file states.jsonl --questions-file questions.json \
  --concurrency 8
```

`ask` and `models list` accept `--timeout`, `--max-retries` and repeatable
`--header 'Name: value'`; `ask` also takes `--extra-body FILE` with extra
top-level request fields. The request id of each response is printed on
stderr and is a `request_id` field in the records.

Profile settings are managed with `config set|get|unset` (`provider`,
`base_url`, `model`, `timeout`, `max_retries` and the global `output`):

```bash
typesafe config set model jev-latest
```

Other commands: `models list` (TypeSafe only), `auth status|logout|token`
and `config path|list|use`.

For automation set `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY`; each
provider reads only its own variable. Global options go before the command:
`-p/--profile`, `-o/--output` (`table`, `json`, `jsonl`, `csv`, `id`) and
`-v/--verbose`.

## Roadmap

- [x] `0.1.0`: scaffold, auth, profiles, `ask`, `models list`
- [x] `0.2.0`: request options, `config set|get|unset`, batch `ask`, request ids
- [x] `1.0.0`: every SDK capability covered, contracts frozen

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

See [LICENSE](LICENSE).
