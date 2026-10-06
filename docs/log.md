# Directory Update Log

## 2026-10-01

* **Initialization**: Initial scaffold (python).
* **Initialization**: Added PyPI Trusted Publishing support (`--publish pypi`).

## 2026-10-02

* **Added**: `cli/batch-ask.md`, `cli/index.md`.
* **Added**: `conventions/public-contract.md`.
* **Changed**: `release/pypi-trusted-publishing.md` names the PyPI project `typesafe-unofficial-cli`.
* **Added**: `cli/question-flags.md`.
* **Added**: `okf-base.yaml`, `make docs-lint`, `tools/docs-retag.py`,
  `conventions/tag-vocabulary.md` and `toolchain/retag-notes.md`.
* **Changed**: the first `make docs-retag` run re-assigned the tags of five
  notes.
* **Change**: the `AGENTS.md` versioning section links to
  `conventions/versioning.md` instead of restating it.
* **Change**: `conventions/tag-vocabulary.md` states the tag form: lowercase, one
  word by default, no parent prefix.
* **Change**: `conventions/versioning.md` names `make release-tag` as the way to
  tag where the `Makefile` defines it.

## 2026-10-05

* **Added**: `cli/questions-file.md`.
* **Added**: `agents/index.md`, `agents/plugin-identity.md`,
  `agents/install-channels.md`, `agents/updates.md`.
* **Change**: `conventions/versioning.md` says the bump commit also sets the
  plugin version.
