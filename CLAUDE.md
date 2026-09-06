# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a **code-modernization case study**, not an application. It contains:

- `CASE_STUDY.md` — the analysis deliverable: why `mailgun/flanker` was chosen as
  a Python modernization target, evidence of staleness (grounded in specific
  files), prioritized modernization opportunities, and a phased roadmap.
- `repos/flanker/` — a shallow clone of the upstream
  [`mailgun/flanker`](https://github.com/mailgun/flanker) repo (`master`
  branch), used as the raw material for the case study. Treat it as read-only
  reference unless a task explicitly asks to modify or fork it.

- `modernization/` — an executed, verified modernization pass (see
  `modernization/RESULTS.md`). `harness/characterize.py` runs flanker's public
  API over `repos/flanker/tests/fixtures` and emits a deterministic JSON
  "golden master"; `harness/compare.py` diffs two such files; `run.sh`
  reproduces the whole thing. `golden/*.json` are the captured outputs.
- `repos/flanker-modern/` — a git worktree of `repos/flanker` on branch
  `modernize` holding the modernized code (commit `8733780`: `six` removed,
  `imghdr`→`flanker/_imagetype.py`, `setup.py`→`pyproject.toml`). Its output is
  byte-identical to `repos/flanker` across the corpus on Python 3.11 and 3.14.
  This branch is published to the fork **`ash-171/flanker`** (remote `fork` in
  `repos/flanker`); `mailgun/flanker` is upstream `origin`.

There is no build/test/lint setup at the project root; the analysis work is
Markdown, and the modernization work lives in `modernization/` + the worktree.
The `.venv-*` directories are disposable (rebuilt by `run.sh` via `uv`).

Earlier drafts of this study targeted `moment/moment` (JS) and then
`html5lib/html5lib-python` (Python). html5lib was rejected as too critical
(≈1.26M downloads/day, vendored in pip until 2022) and because a modernized fork
already exists (`ashleysommer/html5lib-modern`). flanker was chosen as a
medium-sized, genuinely company-abandoned library with no existing modern fork.

## Working on the case study

- Every figure in `CASE_STUDY.md` is meant to be reproducible from the clone.
  Appendix A of that file lists the exact `git log` / `grep` / `find` commands
  behind each number — re-run them in `repos/flanker/` before changing a figure.
- Key evidence files are catalogued in Appendix B of `CASE_STUDY.md`. The
  load-bearing ones: `README.rst` (maintainer disavows the Py3 build),
  `setup.py` (`six` + `standard-imghdr` deps; classifiers stop at Py3.6),
  `flanker/_email.py` / `flanker/dkim.py` / `flanker/mime/message/scanner.py`
  (`six.PY2/PY3` branch patterns), `flanker/mime/message/part.py` (`import
  imghdr`, removed in Python 3.13), `tests/**` (nose-based, won't import on
  Python 3.12+).
- Central thesis to preserve when editing: the modernization is dominated by
  **mechanical transforms** (nose→pytest, drop Python 2 / EOL Python 3, remove
  `six`, `setup.py`→`pyproject.toml`, add type hints), but the test suite must
  be resurrected first — there is no green baseline on a supported interpreter
  today. It is a fork exercise; Mailgun runs a different internal version and
  has disengaged from the public repo.
- §10 of `CASE_STUDY.md` frames execution using the GenAI method from Slalom
  Build's *"Modernizing Legacy Software with GenAI: A Practical Approach"*
  (Garber, 2025): the translation / requirements-extraction / hybrid strategy
  taxonomy, parallel-vs-sequential chunking, complete functionality mapping, and
  a per-functionality workflow — with golden-master (characterization) tests as
  the verification oracle. Keep §10 consistent with §6–§7 if those change; full
  citation is in Appendix C.

## Refreshing the clone

```bash
cd repos/flanker
git fetch --depth 400 origin master && git checkout master && git reset --hard origin/master
```

If commit-cadence, release-date, or file/LOC figures in `CASE_STUDY.md` change
after a refresh, update the "Analyzed" header and the affected tables.

## Commands for the cloned repo (`repos/flanker/`)

Upstream targets Python 2.7 / 3.6 and its test suite uses `nose`, which does not
import on Python 3.12+. From `repos/flanker/`:

| Task | Command |
| --- | --- |
| Create env + install (with extras + test deps) | `python -m venv .venv && . .venv/bin/activate && pip install -e '.[cchardet,validator,tests]'` |
| Run tests (as upstream intends) | `nosetests --with-coverage --cover-package=flanker` |
| Run tests on modern Python | not possible without first porting `nose` → `pytest` (see `CASE_STUDY.md` §6, item 1) |
| Full matrix | `tox` (envs: `py27`, `py36` only) |
| Lint / format | none configured upstream — adding `ruff` is part of the modernization scope |

Upstream has no `pyproject.toml`, no lint/format config, and no type checker —
adding those is the modernization work described in `CASE_STUDY.md`, not
existing tooling.
