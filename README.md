# GenAI-assisted legacy modernization — a verified case study

Modernizing an abandoned Python library **without changing its behavior**, using
a structured GenAI workflow and a characterization-test harness as the safety
net.

**Target:** [`mailgun/flanker`](https://github.com/mailgun/flanker) — an email
address + MIME parsing library (~7k LOC, ~24k downloads/month, no release since
2023, README disavows its own Python 3 build).

**Modernized code:** [`ash-171/flanker` @ `modernize`](https://github.com/ash-171/flanker/tree/modernize)
· [diff vs upstream](https://github.com/ash-171/flanker/compare/master...modernize)
(a fork; this repo is the analysis + verification around it).

![flanker demo: the library parses a mixed address list, converts an internationalized address to punycode, rejects junk, walks a MIME message with a PDF attachment and round-trips it, and scores a bounce — then the same script produces byte-identical output on the pristine library and on Python 3.14](modernization/flanker-demo.gif)

<sub>`bash modernization/demo-both.sh` — flanker's own API (address parsing, MIME walk, bounce scoring) running on the **modernized** code, then the same script's output shown byte-identical against the pristine library and on Python 3.14. ([asciicast](modernization/flanker-demo.cast)) · The verification harness behind the "IDENTICAL" claim is [`run.sh`](modernization/run.sh) ([clip](modernization/flanker-golden-master.gif)).</sub>

---

## Result

The modernized library produces **byte-identical output to the original** across
the entire `tests/fixtures` corpus — 370 address-parse cases, 49 MIME `.eml`
message trees (including round-trip serialization hashes), and 9 bounce-detection
cases — on two Python versions:

| Comparison | Result |
| --- | --- |
| original @ Python 3.11  vs  modernized @ Python 3.11 | **IDENTICAL** |
| original @ Python 3.14  vs  modernized @ Python 3.14 | **IDENTICAL** |
| modernized @ Python 3.11  vs  modernized @ Python 3.14 | **IDENTICAL** |

Changes made (`+259 / −300` lines across 30 files, [full diff](modernization/patches/flanker-modernize.full.diff)):

- **Removed the `six` dependency entirely** — it was imported in 19 modules
  (~120 call sites). `six.text_type`→`str`, `six.moves.*`→stdlib,
  `six.raise_from`→`raise … from`, every `if six.PY2/PY3` branch collapsed to
  the Python 3 arm.
- **Replaced `imghdr`** (removed from the stdlib in Python 3.13; flanker had
  pinned the `standard-imghdr` backport) with a faithful ~100-line port,
  `flanker/_imagetype.py`.
- **`setup.py` → `pyproject.toml`** (PEP 621), `requires-python = ">=3.9"`.
- Install-time dependencies: **13 → 11**.

---

## Why this is interesting

flanker's own test suite can't run on any currently-supported Python — `nose`
1.3.7 fails to import even on 3.11 (`collections.Callable` was removed in 3.10).
So there was **no baseline to modernize against**.

The fix: build a **characterization ("golden master") harness** that captures the
library's observable behavior over a fixed corpus as a deterministic JSON
document, then require the modernized code to reproduce it exactly. That harness
is the reusable, transferable part of this project — it's how you refactor
safely when the tests are gone.

The modernization strategy follows Diego Garber's *"Modernizing Legacy Software
with GenAI: A Practical Approach"* (Slalom Build, 2025) — its
translation / requirements-extraction / hybrid taxonomy and per-functionality
workflow — adapted to a small, same-language job. See
[`CASE_STUDY.md` §10](CASE_STUDY.md).

---

## Repository map

| Path | What |
| --- | --- |
| [`CASE_STUDY.md`](CASE_STUDY.md) | The full analysis: why flanker, evidence of staleness, the GenAI method applied (§10), the prioritized roadmap. |
| [`modernization/RESULTS.md`](modernization/RESULTS.md) | Run write-ups — run 1 (drop Python 2 / `six` / `setup.py`) and run 2 (`nose`→`pytest`): exactly what changed and every comparison result. |
| [`writeup/blog-draft.md`](writeup/blog-draft.md) | Narrative write-up (draft): the problem, the golden-master approach, and how the work was done in Claude Code. |
| `modernization/harness/characterize.py` | Runs flanker's public API over the corpus → deterministic golden-master JSON. |
| `modernization/harness/compare.py` | Structural diff of two golden-master files. |
| `modernization/run.sh` | One command: build both versions, characterize, compare. |
| `modernization/demo.py` · `demo-both.sh` | A readable tour of flanker's API (address parsing, MIME walk, bounce scoring); `demo-both.sh` runs it on the modernized code and shows the output is byte-identical to the pristine library and on Python 3.14. |
| `modernization/golden/*.json` | Captured outputs (original + modernized, Python 3.11 + 3.14). |
| `modernization/patches/` | The modernization as a git patch + a plain diff. |
| `CLAUDE.md` | Working notes for AI coding assistants on this repo. |

The modernized flanker source itself is not vendored here. It lives on the
[`modernize` branch of the `ash-171/flanker` fork](https://github.com/ash-171/flanker/tree/modernize)
(GitHub renders the [full diff vs `mailgun:master`](https://github.com/ash-171/flanker/compare/master...modernize)),
and is also reproducible from the pinned upstream commit plus the patch in
`modernization/patches/` (see below).

---

## Reproduce

Requires [`uv`](https://docs.astral.sh/uv/) (for pinned Python builds) and `git`.

```bash
# 1a. the pristine target at the exact analyzed commit
git clone https://github.com/mailgun/flanker repos/flanker
git -C repos/flanker checkout c7f7073

# 1b. the modernized code — either clone the fork branch ...
git clone --branch modernize https://github.com/ash-171/flanker repos/flanker-modern

#     ... or rebuild it locally from the patch (no fork needed):
#   git -C repos/flanker worktree add ../flanker-modern -b modernize
#   git -C repos/flanker-modern apply ../../modernization/patches/flanker-modernize.full.diff

# 2. build both, characterize, compare
bash modernization/run.sh
```

Expected tail: `IDENTICAL - modernized flanker matches baseline on the full corpus`.

You can also just re-diff the committed evidence without rebuilding anything:

```bash
python modernization/harness/compare.py \
  modernization/golden/baseline.json modernization/golden/modern.json
```

---

## Scope & honesty

- This is a **personal modernization exercise**. It is **not merged, adopted, or
  endorsed** by Mailgun.
- **Phases 0–1** are done: the `nose`→`pytest` port (suite now runs green on
  Python 3.11 and 3.14 — `255 passed, 6 skipped, 5 xfailed`) and the mechanical
  "translation" slice (drop Python 2, remove `six`, `setup.py`→`pyproject.toml`).
  Not yet done: type hints + `py.typed` (Phase 2), the `WebOb` dependency audit
  and PLY-table regeneration story (Phase 3). See the roadmap in
  `CASE_STUDY.md` §7.
- "Byte-identical across the corpus" is a strong empirical result over ~428
  cases — it is evidence of behavioral equivalence, not a formal proof.

---

## Credits

- Target library: [`mailgun/flanker`](https://github.com/mailgun/flanker),
  Apache-2.0, © Mailgun Technologies Inc.
- Method: [*Modernizing Legacy Software with GenAI: A Practical Approach*](https://medium.com/slalom-build/modernizing-legacy-software-with-genai-a-practical-approach-2cfc5b67d467),
  Diego Garber, Slalom Build, 2025.
