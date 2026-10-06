# Profiles and providers

A profile bundles a provider, base URL, model, timeout and retry count. The
provider is `typesafe` (`https://api.typesafe.ai`) or `openrouter`
(`https://openrouter.ai/api`).

| Provider     | Environment variable  |
| ------------ | --------------------- |
| `typesafe`   | `TYPESAFE_API_KEY`    |
| `openrouter` | `OPENROUTER_API_KEY`  |

Each provider reads only its own variable, so a key is never sent to the
other provider's host.

- Select a profile per call with `-p NAME` or `TYPESAFE_CLI_PROFILE`; set the
  default with `config use NAME`.
- `auth login` for OpenRouter makes one minimal billed request to validate
  the key; skip it with `--skip-validation`. `auth status --check` bills one
  too on OpenRouter. A TypeSafe key is validated for free.
- `models list` works on TypeSafe only.
- `config list` shows the profiles; `config path` prints the settings file.
- `--insecure-storage` stores the key in a 0600 file instead of the keyring;
  use it only where no keyring exists.
