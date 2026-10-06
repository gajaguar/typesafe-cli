# Batch mode

```bash
typesafe -o jsonl ask --states-file states.jsonl \
  --questions-file questions.yaml --concurrency 8
```

- Input: one JSON value per line (string, object or array). Blank lines are
  skipped; a state's `index` counts the non-blank lines from zero.
- Every record carries its state's `index`; output stays grouped by state in
  input order however the requests finish.
- Token totals and the number answered go to stderr.
- A failed state does not stop the others. Answers are rendered first, then
  each failure is reported on stderr as `state <index>: <message>`, and the
  exit code is the one the first failed state maps to. A batch with a failure
  never exits 0.
- `--states-file` cannot be combined with `--state` or `--state-file`.
