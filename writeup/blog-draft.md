# Modernizing an abandoned Python library when its tests can't run

*Draft — by Aswathi ([@ash-171](https://github.com/ash-171)). Companion to the
[flanker modernization case study](https://github.com/ash-171/flanker-modernization-case-study).*

---

## TL;DR

I took [`mailgun/flanker`](https://github.com/mailgun/flanker) — a ~7,000-line
Python email-address and MIME parser that hasn't had a real release since 2023
and whose own README disavows its Python 3 build — and modernized it **without
changing its behavior**: dropped the `six` / Python 2 straddle, replaced a
stdlib module that no longer exists, moved to `pyproject.toml`, and ported the
test suite from `nose` to `pytest`.

The catch: flanker's tests couldn't run on *any* supported Python, so there was
no green baseline to protect. The fix was to build a **characterization
("golden master") harness** — pin the library's observable behavior over a
fixed corpus as deterministic JSON, then require the modernized code to
reproduce it byte-for-byte.

Result: identical output across ~428 cases on Python 3.11 **and** 3.14, and a
test suite that runs green (`255 passed, 6 skipped, 5 xfailed`) on a modern
interpreter for the first time.

I did the work in **Claude Code**. The interesting part isn't "AI wrote the
code" — it's *which* parts an agent is good at, and the one bug it introduced
that only the resurrected test suite caught.

---

## Why flanker

I wanted a modernization target that was real but not reckless to touch:

- **Genuinely abandoned, not merely quiet.** flanker's `README.rst` says
  outright: *"We are not using Flanker with Python 3 in the house… use at your
  own risk."* Mailgun runs an older internal fork (v0.8.5 lineage) and has
  disengaged from the public repo. There were **zero commits in 2024 and
  2025**; the only 2026 activity is four commits that do the bare minimum to
  keep the package importable on Python 3.13 (*"add backport to deprecated
  library"*, *"make regex patterns raw strings"*) and nothing else.
- **Medium-sized and self-contained.** 49 library modules, ~6,950 LOC, one
  well-bounded domain (email parsing).
- **Not critical shared infrastructure**, and **no existing modernized fork** —
  so the exercise is useful rather than redundant, and a mistake doesn't ripple
  through the ecosystem.

The staleness is a deep Python 2/3 straddle: `six` imported across **19 of 49
modules** (~120 call sites), no type annotations anywhere, a bare `setup.py`,
and a `nose`-based test suite.

## The problem: you can't refactor safely without a test to break

`nose` 1.3.7 doesn't import on Python 3.10+ — `collections.Callable` was moved
to `collections.abc` and `nose` never caught up:

```
AttributeError: module 'collections' has no attribute 'Callable'
```

So flanker's ~950 assertions were dead weight. Any change I made — however
mechanical — would be unverified. "It's just find-and-replace" is exactly the
kind of confidence that ships a regression into a MIME parser.

### Characterization tests

The standard move for this situation (Feathers' *Working Effectively with
Legacy Code*, chapter 13) is a **characterization test**: don't assert what the
code *should* do, capture what it *does* do and lock it down.

The harness (`modernization/harness/characterize.py`) runs flanker's public API
over the repository's own `tests/fixtures` and serializes the results to a
sorted, timestamp-free JSON document:

- **370 address-parse cases** (`mailbox_valid/invalid.txt`,
  `abridged_localpart_valid/invalid.txt`), each in strict and lenient mode —
  capturing class, `address`, `display_name`, `hostname`, `full_spec`,
  `requires_non_ascii`, `str()`, and any exception raised.
- **49 MIME `.eml` fixtures** through `mime.from_string` — a full recursive part
  walk (content type / disposition / encoding, ordered headers, decoded-body
  SHA-256, child parts) **plus a round-trip `to_string()` hash** to catch
  serialization drift.
- **9 bounce fixtures** through `msg.bounce` — `is_bounce`, `score`, `status`,
  `notification`, `diagnostic_code`.

Two runs of the same install diff clean. Now "did I change behavior?" is one
command:

```bash
bash modernization/run.sh
# >> comparing
# IDENTICAL - modernized flanker matches baseline on the full corpus
```

This harness is the reusable, transferable part of the whole project. The
flanker-specific diffs are throwaway; "capture behavior as data, then hold the
refactor to it" travels to any legacy codebase.

## The method

I framed execution with Diego Garber's *["Modernizing Legacy Software with
GenAI: A Practical Approach"](https://medium.com/slalom-build/modernizing-legacy-software-with-genai-a-practical-approach-2cfc5b67d467)*
(Slalom Build, 2025): its translation / requirements-extraction / hybrid
taxonomy, and the discipline of a per-functionality workflow with a
verification oracle. This job is overwhelmingly **translation** — same
behavior, newer idiom — which is the case where a golden master works best and
where an AI agent is most useful.

I split it into phases so each commit is reviewable on its own:

### Phase 1 — drop the Python 2 machinery

- **Removed `six` entirely.** `six.text_type`→`str`, `six.moves.*`→stdlib,
  `six.raise_from(e, c)`→`raise e from c`, every `if six.PY2/PY3` branch
  collapsed to the Python 3 arm. 19 modules, ~120 call sites.
- **Replaced `imghdr`.** It was removed from the stdlib in Python 3.13; flanker
  had pinned the `standard-imghdr` backport. I ported CPython's recognizer set
  into a ~100-line `flanker/_imagetype.py` with identical return values.
- **`setup.py` → `pyproject.toml`** (PEP 621), `requires-python = ">=3.9"`,
  classifiers through 3.14. Install-time dependencies: **13 → 11**.

`+259 / −300` lines across 30 files. Golden master: **IDENTICAL** on Python 3.11
and 3.14.

### Phase 0 — `nose` → `pytest`

Numbered 0 because it should have come first — but it needed the golden master
to exist, since the port can't verify itself.

- **942 `nose.tools` assertions → bare `assert`** across the test suite (~30
  files):
  `eq_(a, b)` / `assert_equal` → `assert a == b`, `ok_` → `assert x`,
  `assert_raises(E, f, x)` → `with pytest.raises(E): f(x)` (11 sites).
- `nose.tools.nottest` → a 3-line shim (`func.__test__ = False`); still needed
  because the suite has helper functions named `*_test` and I configured pytest
  to collect that legacy naming rather than mass-rename 142 functions.
- `from nose import SkipTest` → `unittest`; the standalone `mock` backport →
  `unittest.mock`; `six` removed from the 9 test modules still using it.
- `[tool.pytest.ini_options]` in `pyproject.toml`; a `conftest.py` registering
  `--no-skip`; `.travis.yml` (Python 2.7 / 3.6, `nosetests`) →
  `.github/workflows/ci.yml` (3.9–3.13 matrix, `pytest`).

**`255 passed, 6 skipped, 5 xfailed`** — identical on CPython 3.11 and 3.14.
Test code only; no `flanker/` runtime change, so the Phase 1 golden-master
result still holds.

The 5 `xfail`s are pre-existing breakage that has nothing to do with the
framework port, each marked with a reason and left for later phases:
`cryptography` 3.0 (2020) removed `RSAPrivateKey.signer()`; `email.mime.audio._whatsnd`
is gone on Python 3.11+; two fixtures encode charset-detection output that
predates modern `chardet`. Marking them `xfail` keeps the suite honest *and*
green — a reviewer sees exactly what's deferred instead of a wall of red.

## How Claude Code was used — and the bug it caught

I ran the whole thing in [Claude Code](https://www.anthropic.com/claude-code).
Being specific about the division of labor, because "AI modernized a library"
is not a useful claim:

**The agent did the mechanical bulk, as scripts — not 942 hand edits.** It
wrote a small AST-aware Python rewriter for the `nose.tools` → `assert`
conversion (balance parens across line continuations, split arguments on the
top-level comma, re-emit as `assert`), ran it, showed me the diff, and iterated.
Same for the import rewrites and the `six` collapses. It stood up the
characterization harness, wired the CI, and drove the
edit → run pytest → read failures → fix loop.

**I did the judgment.** Which library to target and why. What the golden-master
corpus should cover (the round-trip serialization hash was the important call —
without it, a `to_string()` regression walks straight through). Where the phase
boundaries are. Which failures are "port bugs" versus "pre-existing, `xfail`
it."

**The cautionary tale.** The first pass of the assertion rewrite turned

```python
assert_equal('parsing' in m, True)
```

into

```python
assert 'parsing' in m == True
```

which *looks* right and is **wrong** — Python chains comparisons, so that parses
as `('parsing' in m) and (m == True)`, and `m` is a dict, so `m == True` is
`False` and the assertion fails for the wrong reason. Four tests went red. The
fix was to teach the rewriter to parenthesize any operand containing a
comparison or boolean operator:

```python
assert ('parsing' in m) == True
```

The point isn't that the agent made a mistake — a careful human doing 942 edits
makes that mistake too. The point is that **the resurrected test suite caught
it immediately**, and without the golden master + the `pytest` port there would
have been nothing to catch it. Mechanical modernization by an agent is only as
safe as the oracle you check it against.

## Honesty box

- This is a **personal exercise**. It is not merged, adopted, or endorsed by
  Mailgun. The one slice that stands on its own — dropping the `standard-imghdr`
  dependency — is filed upstream as
  [mailgun/flanker#275](https://github.com/mailgun/flanker/pull/275), but the
  repo has years of unreviewed PRs, so that's "submitted," not "landed."
- **"Byte-identical across the corpus"** is strong empirical evidence over ~428
  cases — it is not a formal proof of equivalence. A behavior not exercised by
  a fixture is not covered.
- **Phases 2–3 are not done:** type hints + `py.typed`, a `WebOb` dependency
  audit, and the PLY parser-table regeneration story.
- `cchardet` has no wheels for modern Python; the suite runs without it (pure
  `chardet`), which is what surfaces two of the `xfail`s.

## Takeaways

1. **When the tests are gone, characterization tests are how you refactor
   safely** — and the harness, not the diff, is the artifact worth keeping.
2. **Translation-style modernization is a good fit for an AI agent** *provided
   there's a verification oracle.* The ratio of rote transform to judgment is
   high, and the rote part is exactly what you don't want to do by hand.
3. **Have the agent write the transform as a script, not as N manual edits** —
   it's reviewable, re-runnable, and its mistakes are systematic (and therefore
   catchable) rather than scattered.
4. **Separate "make it run" from "make it good" from "pre-existing bugs."** Phase
   0/1 vs. type hints vs. `xfail`-with-a-reason. Each commit stays reviewable,
   and nobody has to guess which red is new.

---

*Code: [`ash-171/flanker` @ `modernize`](https://github.com/ash-171/flanker/tree/modernize)
· analysis + harness: [`flanker-modernization-case-study`](https://github.com/ash-171/flanker-modernization-case-study)
· method: Garber, [Slalom Build, 2025](https://medium.com/slalom-build/modernizing-legacy-software-with-genai-a-practical-approach-2cfc5b67d467).*
