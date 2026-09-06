# Golden-master captures

Deterministic snapshots of flanker's observable behavior over
`repos/flanker/tests/fixtures`, produced by `../harness/characterize.py`.

| File | Library | Python |
| --- | --- | --- |
| `baseline.json` | pristine `mailgun/flanker` @ `c7f7073` | 3.11 |
| `modern.json` | modernized (branch `modernize`) | 3.11 |
| `baseline-py314.json` | pristine | 3.14 |
| `modern-py314.json` | modernized | 3.14 |

Compare any two with `../harness/compare.py A.json B.json` (it ignores the
informational `_env` block). All four are equal on the behavioral data.

Regenerate with `bash ../run.sh` from the project root.
