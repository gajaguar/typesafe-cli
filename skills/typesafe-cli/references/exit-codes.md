# Exit codes

| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| 0    | OK                                                |
| 1    | Generic failure                                   |
| 2    | Usage error (bad flags or input; no request sent) |
| 3    | Configuration problem                             |
| 4    | Authentication failed                             |
| 5    | Forbidden                                         |
| 6    | Not found                                         |
| 7    | Validation error from the API                     |
| 8    | Rate limited                                      |
| 9    | Service unavailable                               |

In batch `ask`, a failed state never stops the others, but the exit code is
the one the first failed state maps to, so a batch with a failure never
exits 0.

Source of truth: `src/typesafe_unofficial_cli/runtime/exit_codes.py`.
