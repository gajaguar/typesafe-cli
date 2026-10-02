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

Other commands: `models list` (TypeSafe only), `auth status|logout|token`
and `config path|list|use`.

For automation set `TYPESAFE_API_KEY` or `OPENROUTER_API_KEY`; each
provider reads only its own variable. Global options go before the command:
`-p/--profile`, `-o/--output` (`table`, `json`, `jsonl`, `csv`, `id`) and
`-v/--verbose`.

## Roadmap

- [x] `0.1.0`: scaffold, auth, profiles, `ask`, `models list`
- [ ] `1.0.0`: every SDK capability covered, contracts frozen

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

See [LICENSE](LICENSE).
