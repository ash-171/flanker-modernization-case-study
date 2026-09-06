# Code Modernization Case Study: flanker (Python)

**Repository:** [`mailgun/flanker`](https://github.com/mailgun/flanker)
**Analyzed:** 2026-09-06 · `master` branch @ `c7f70738` (2026-04-08)
**Local clone:** `repos/flanker/` (shallow, depth 400)
**Prepared by:** Aswathi ([@ash-171](https://github.com/ash-171))

---

## 1. Executive summary

`flanker` is an email **address-parsing and MIME-parsing** library that Mailgun
open-sourced in 2013. It is a good modernization subject precisely because it is
*not* critical shared infrastructure: it is a self-contained, ~7,000-LOC library
in a security-sensitive but well-bounded domain, with a modest and mostly
Mailgun-adjacent dependent base, and **no existing modernized fork**.

The staleness here is unusually well-signposted by the maintainer:

- `README.rst` states plainly: *"Flanker is heavily used by Mailgun in
  production with Python 2.7. The current production version is v0.8.5… We are
  not using Flanker with Python 3 in the house… use at your own risk."* The
  owning company runs an **older internal fork** and disclaims the public
  Python 3 build.
- `CHANGELOG.md` stops having real entries in 2019 and says *"The only reliable
  source of information is the commit log."*
- Commit activity: **0 commits in all of 2024 and 2025**, then 4 commits in
  April 2026 whose messages are literally *"add backport to deprecated
  library"* and *"make regex patterns raw strings to avoid SyntaxWarning"* —
  the minimum work to keep the package importable on Python 3.13, and nothing
  else.

The codebase is a deep Python 2/3 straddle: `six` is a runtime dependency used
across **19 of 49 modules** (~120 call sites), there are no type annotations
anywhere, packaging is a bare `setup.py`, and the test suite is written for
**`nose`**, which no longer imports on modern Python. Modernization is almost
entirely mechanical — but the test suite has to be resurrected first, or the
work is being done blind.

**Execution method:** §10 applies the GenAI modernization approach from Slalom
Build's *"Modernizing Legacy Software with GenAI: A Practical Approach"* (Garber,
2025) — its translation / requirements-extraction / hybrid taxonomy, its
chunking discipline, and its per-functionality workflow — to this specific
repo, and adds a golden-master verification corpus as the objective oracle that
method needs.

---

## 2. Why this repository was selected

**Selection criteria (revised after rejecting `html5lib`):**

| Criterion | Requirement | flanker |
| --- | --- | --- |
| Language | Python | ✅ Pure Python |
| Size | Medium | ✅ 49 library modules, ~6,950 LOC; 38 test files |
| Real usage | Real, but **not** critical transitive infrastructure | ✅ Niche (email/MIME); modest dependent base; never vendored into pip etc. |
| Genuine staleness | Stale, maintainer-acknowledged | ✅ No real release since 2023; README disavows the Py3 build; 0 commits in 2024–2025 |
| No existing modern fork | Modernization not already done elsewhere | ✅ No maintained Python-3-modernized fork exists |
| Company-abandoned | Clear "opened, then walked away" story | ✅ Mailgun runs an older internal version; public repo on life support |
| Clear modernization thesis | Concrete, low-risk transforms | ✅ nose→pytest, drop Py2, remove `six`, `setup.py`→`pyproject.toml`, add types |

**Why `html5lib` was rejected as the target:** it turned out to be critical
infrastructure — ~1.26M downloads/day, ~1,060 dependent PyPI packages, and it
was vendored *inside pip itself* until pip 22.2 (2022). It also already has a
modernized fork ([`ashleysommer/html5lib-modern`](https://github.com/ashleysommer/html5lib-modern):
Py3.8+, `six` removed, `pyproject.toml`). Both facts make it a poor "modernize
it yourself" target, even though it is a fine object of analysis.

**Other candidates considered:** `nvbn/thefuck` (recognizable, medium, but still
sporadically maintained); `clips/pattern` (very stale, but academic/niche and
large); `spotify/luigi` (superseded by Airflow, but still releasing).

---

## 3. Repository snapshot

| Attribute | Value |
| --- | --- |
| Purpose | Email address parsing (`flanker.addresslib`) + MIME parsing (`flanker.mime`) |
| Owner / license | Mailgun Technologies Inc. / Apache 2.0 |
| Releases | v0.9.11 (Dec 2019) · v0.9.14 (Mar 2021) · v0.9.15 (Feb 2023) · **v0.9.16 (Apr 2026 — survival patch only)** |
| Repo activity | 2020: 5 commits · 2021: 3 · 2022: 1 · **2023: 3 · 2024: 0 · 2025: 0** · 2026: 4 (all April) |
| Default branch | `master` |
| Library size | 49 modules, ~6,950 LOC across `addresslib/` (+ `_parser/`, `plugins/`, `drivers/`) and `mime/` |
| Tests | 38 files, written for **`nose`** (`from nose.tools import eq_, ok_, …`) + external `mock` |
| Runtime deps | `attrs`, `chardet`, `cryptography`, `idna`, `ply`, `regex`, **`six`**, **`standard-imghdr==3.13.0`**, `tld`, `WebOb` |
| Optional extras | `dnsq` + `redis` (address validator), `cchardet` |
| Declared Python support | Classifiers: Python **2, 2.7, 3, 3.6** only; no `python_requires` |
| Packaging | `setup.py` only — **no `pyproject.toml`, no `setup.cfg`** |
| Lint/format | **none** — no flake8/pylint/ruff/black config in the repo |
| CI | `.travis.yml` (Travis CI; Python 2.7 + 3.6) + Coveralls |

---

## 4. Evidence of staleness

Every claim below is grounded in a specific file in the clone.

### 4.1 The maintainer has publicly stepped back

`README.rst`, verbatim:

> "Flanker is heavily used by Mailgun in production with Python 2.7. The current
> production version is v0.8.5. Support for Python 3 was added in v0.9.0 by
> popular demand from the community. **We are not using Flanker with Python 3 in
> the house.** All we know is that tests pass with Python 3.6, so **use at your
> own risk.**"

`CHANGELOG.md` last substantive entry is dated **2019-09-25**, followed by:
*"The only reliable source of information is the commit log."*

### 4.2 The 2026 commits are decay maintenance, not development

The only activity since 2023 (`git log --since=2025-01-01`):

| Date | Message |
| --- | --- |
| 2026-04-06 | *add backport to deprecated library; make regex patterns raw strings to avoid SyntaxWarning upon Python string parsing* |
| 2026-04-08 | *update setup.py version* → tagged **v0.9.16** |

- *"backport to deprecated library"* = adding `standard-imghdr==3.13.0` to
  `install_requires` because `flanker/mime/message/part.py` does
  `import imghdr`, and **`imghdr` was removed from the standard library in
  Python 3.13**. The response was to depend on a copy of the deleted module,
  not to replace ~5 lines of magic-byte sniffing.
- *"raw strings to avoid SyntaxWarning"* = invalid escape sequences in `regex`
  patterns, a Python 3.12 `SyntaxWarning` that becomes a `SyntaxError` in
  future versions.

### 4.3 Deep Python 2/3 straddle via `six`

`six` is in `install_requires` and imported in **19 of 49** library modules.
Call-site census (`grep -rho '\bsix\.[a-zA-Z_]+'`, excluding tests):

| Symbol | Count | Modern equivalent |
| --- | --- | --- |
| `six.text_type` | 29 | `str` |
| `six.PY2` / `six.PY3` | 27 | delete the branch, keep the Py3 arm |
| `six.binary_type` | 16 | `bytes` |
| `six.string_types` | 9 | `(str,)` / `str` |
| `six.moves` (`StringIO`, `range`, `urllib_parse`) | 7 | `io.StringIO`, `range`, `urllib.parse` |
| `six.unichr` | 3 | `chr` |
| `six.BytesIO` / `six.StringIO` | 3 | `io.BytesIO` / `io.StringIO` |
| `six.raise_from` | 1 | `raise X from Y` |
| `six.iteritems` / `six.itervalues` | 2 | `.items()` / `.values()` |

Typical pattern (`flanker/dkim.py`, `flanker/_email.py`, `flanker/mime/message/scanner.py`):

```python
if six.PY3 and isinstance(selector, six.text_type):
    selector = selector.encode('utf-8')
```

— pure "on Python 3, this is text, so encode it" guards that collapse to
unconditional code once Python 2 is dropped.

### 4.4 No type information

`grep -rE 'def .*\) *->' flanker` (excluding tests) returns **0**. The public
entry points — `flanker.addresslib.address.parse` / `parse_list`,
`flanker.mime.from_string` — are unannotated, and there is no `py.typed`.

### 4.5 Legacy source and packaging conventions

- **14 modules** carry a `# coding:` / `# -*- coding: utf-8 -*-` header
  (unnecessary since Python 3, which is UTF-8 by default).
- `type(value) == list` instead of `isinstance(value, list)`
  (`flanker/mime/message/headers/encoding.py`).
- Packaging is a single 45-line `setup.py`; `long_description=open('README.rst').read()`;
  `tests_require` with a trailing-comma bug that makes it a 1-tuple.
- `flanker/addresslib/_parser/` commits **six generated PLY tables**
  (`*_parsetab.py`, 9–12 KB each) into source control.

### 4.6 The test suite does not run on modern Python

All 38 test files use **`nose`** (`from nose.tools import eq_, ok_,
assert_equal, *`) plus the external **`mock`** package (folded into the stdlib
as `unittest.mock` since Python 3.3). `nose` has been unmaintained since ~2015
and fails to import on Python 3.12+ (it uses the removed `imp` module). CI is
`.travis.yml` on Python 2.7 and 3.6 — Travis CI dropped free OSS minutes in
2021. **There is currently no way to get a green test baseline on a supported
interpreter without first porting the suite.**

---

## 5. What is *not* wrong (and must be preserved)

- **Self-contained and pure Python** — no C extensions; `cchardet` and the
  Redis/DNS validator are optional extras.
- **A real test corpus exists** (38 files, MIME fixtures, address-grammar
  cases) — once ported to `pytest` it is a usable regression oracle.
- **Bounded, stable public API** — a handful of parse/serialize entry points in
  `flanker.addresslib.address` and `flanker.mime`.
- **The grammar is deliberate.** `flanker/addresslib/_parser/` encodes RFC
  2822/5322 address syntax via PLY; the tables are checked in for a reason
  (no build-time codegen). Regeneration must stay reproducible.

---

## 6. Modernization opportunities (prioritized)

| # | Change | Impact | Effort | Risk | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | **Port tests `nose` → `pytest`**; drop external `mock` for `unittest.mock` | High | Med | Low | Prerequisite for everything else — the suite can't run today. Mechanical: `eq_(a, b)`→`assert a == b`, `ok_(x)`→`assert x`, `assert_raises`→`pytest.raises`. |
| 2 | Replace `.travis.yml` with **GitHub Actions**; matrix on supported Pythons; coverage via `pytest-cov` | High | Low | Low | Gives a green baseline to modernize against. |
| 3 | `setup.py` → **`pyproject.toml`** (PEP 621 + build backend); fix the `tests_require` tuple bug | Med | Low | Low | |
| 4 | Drop **Python 2.7 / 3.6**; set `requires-python = ">=3.9"` | High | Low | Low | Enabling change for #5. Metadata + CI only. |
| 5 | **Remove `six`** (19 modules, ~120 sites) and Py2-only branches | High | Med | Low | Table in §4.3 is the full transform list. Drops a runtime dependency. Gate on the ported suite. |
| 6 | Replace `imghdr` / `standard-imghdr` with a small magic-byte check (or `puremagic`/`filetype`) | Med | Low | Low | Removes a hard pin on a backport of deleted stdlib code. |
| 7 | Add **`ruff` + `ruff format` + `pre-commit`** | Med | Low | Low | The repo currently has *no* lint/format config at all. |
| 8 | Add **type hints** to the public API; ship `py.typed`; wire `mypy` into CI | High | Med | Low | Biggest downstream benefit; can land incrementally. |
| 9 | Audit the **`WebOb`** dependency (a full WSGI request/response library) used only for a few MIME helpers | Med | Med | Med | Likely replaceable with stdlib `email` + small helpers. |
| 10 | Document / script **PLY table regeneration**; re-evaluate `ply` (itself low-activity) vs a maintained parser | Low | Med | Med | Only if parser work is needed; keep behavior identical. |
| 11 | Governance: decide whether this fork is adopted, retired, or merged with Mailgun's internal lineage | — | — | — | README currently disowns the Py3 build. Realistically a community fork. |

---

## 7. Proposed roadmap

**Phase 0 — Make the project testable on modern Python (no behavior change)**
- Port the `nose` suite to `pytest`; replace `mock` with `unittest.mock` (#1).
- Travis → GitHub Actions; establish a green run on Python 3.9–3.13 as the
  baseline every later phase must preserve (#2).

**Phase 1 — `1.0`: drop Python 2 and the compat layer (public API unchanged)**
- `pyproject.toml`; delete `setup.py` (#3).
- `requires-python = ">=3.9"`; trim classifiers and CI matrix (#4).
- Remove `six` and all `six.PY2/PY3` branches (#5).
- Replace `imghdr`/`standard-imghdr` (#6).
- Add `ruff` + `pre-commit` (#7).
- Every change gated on the Phase 0 suite passing unchanged.

**Phase 2 — Typing and dependency diet**
- Annotate the public API, add `py.typed`, add `mypy` to CI (#8).
- Evaluate and, if feasible, drop `WebOb` (#9).

**Phase 3 — Parser and governance**
- Script PLY table regeneration; decide `ply`'s future (#10).
- Resolve the maintenance-ownership question (#11); re-check the address
  grammar against current RFC 5321/5322 and HTML `type=email` rules.

Phases 0–1 are deterministic and independently shippable. Phase 2 is
incremental. Phase 3 needs a decision-maker.

---

## 8. Risks and constraints

- **No usable baseline exists yet.** Until Phase 0 lands, there is no green test
  run on a supported interpreter — any refactor before that is unverifiable.
  This is the single most important sequencing constraint.
- **Security-sensitive domain.** Email address and MIME parsing sit on the
  boundary of header injection, address spoofing, and MIME-type confusion
  attacks. All Phase 1 changes must be strictly behavior-preserving, checked
  against a fixed fixture corpus.
- **`six` removal touches 19 files but is behavior-neutral on Python 3** — still
  needs the full suite, because some shims (`text_type` encode/decode guards in
  `scanner.py`, `dkim.py`) sit in hot parsing paths.
- **Upstream may not merge large PRs.** Mailgun runs an older internal lineage
  (`v0.8.5`-based) and has disengaged from the public Python 3 build. Realistic
  delivery is a maintained fork.
- **PLY tables are generated artifacts checked into the tree.** Regeneration
  must be reproducible, or address-parsing behavior can shift silently.

---

## 9. Recommendation

For a modernization *project* (learning-oriented or portfolio), the ideal scope
is **Phase 0 + Phase 1 on a fork**, in this order:

1. Port `nose` → `pytest`, get CI green on Python 3.13 (this is most of the
   work, and the part with real technique in it).
2. Add `pyproject.toml`; delete `setup.py`.
3. Set `requires-python = ">=3.9"`; trim CI and classifiers.
4. Remove `six` across all 19 modules; delete the `six.PY2/PY3` branches.
5. Replace the `imghdr` backport with a few lines of magic-byte detection.
6. Add `ruff` + `pre-commit`.
7. Prove equivalence: the ported fixture suite passes identically before and
   after every step.

Deliverables are concrete and measurable: a test suite that runs green on a
current interpreter (where there is none today), a `pyproject.toml`, `six` and
`standard-imghdr` gone from `install_requires`, ~19 files de-`six`-ed, and a
`ruff`-clean tree — with zero changes to parsing behavior. Type hints (Phase 2)
are the natural next pass; the `WebOb` diet and the governance question are
follow-ups to document, not code for a single sprint.

---

## 10. Executing this with GenAI — applying Slalom Build's practical approach

This section maps the method in Diego Garber's *"Modernizing Legacy Software
with GenAI: A Practical Approach"* (Slalom Build, 25 Jul 2025) onto the flanker
work above. The article proposes three modernization strategies, a
context/chunking discipline, and a per-functionality workflow.

### 10.1 The article's three strategies, applied to flanker

| Strategy (article) | What it is | Fit for flanker |
| --- | --- | --- |
| **Direct code translation** | LLM rewrites code into a new language/platform 1:1, preserving structure. Fast, but *"modernizes syntax only; preserves legacy problems"* — technical debt and quirks transfer unchanged. | The **default** here. flanker is not changing language — it is moving from Python 2/3-straddle to modern Python 3. `six` removal, `# coding` header deletion, `imghdr` replacement, `nose`→`pytest` assert rewrites, `setup.py`→`pyproject.toml` are all structure-preserving transforms an LLM can do file-by-file. |
| **Requirements extraction & reimplementation** | LLM extracts functional requirements from the legacy code, then generates a fresh implementation from those requirements. Risk: *"loss of subtle implementation details."* | **Too aggressive for most of flanker** — the parsing edge cases *are* the value, and the article's own warning (subtle detail loss) is acute in RFC 5322 / MIME territory. Reserve it for genuinely rotten corners: the `WebOb` usage (extract "what request/response helper do we actually need", reimplement on stdlib) and possibly `flanker/mime/message/fallback/`. |
| **Hybrid (article's recommendation)** | Extract requirements *and* keep the legacy code as the functional reference; reimplement with modern patterns while the old code pins behavior. | The right call for the **judgement-heavy** items: normalizing flanker's inconsistent return conventions (some paths return `None`, some an empty `AddressList`, some raise), the broad `except Exception` swallow in `headers/encoding.py`, and any decision about the PLY parser. Extract the rule, keep the old function + its tests as the oracle, change the shape. |

**Takeaway:** flanker is a *translation-dominant* job with a few *hybrid*
pockets and one or two *reimplementation* candidates — the opposite mix from the
enterprise rewrites the article targets, but the same decision framework.

### 10.2 Context & chunking

The article's chunking machinery exists because *"enterprise codebases exceed
millions of lines"* against a ~200K-token window. **flanker is ~6,950 LOC** —
the entire library fits in one modern context window. So:

- **Parallel chunking** (independent sub-tasks, recombined) is the natural mode:
  de-`six` each module (or small cluster) in its own focused session.
- **Sequential chunking** (feed each chunk's output as the next chunk's input)
  is only needed for the cross-cutting passes — e.g. deciding a single
  bytes/str convention and threading it through `scanner.py` →
  `part.py` → `headers/encoding.py` in order.
- **Complete functionality mapping** still applies even at this size: address
  *validation* spans `addresslib/address.py` + `validate.py` + `plugins/*` +
  `drivers/*` + DNS; never hand the LLM just one of those files.

### 10.3 Per-functionality workflow (article's 5 steps → flanker)

1. **Extract a functionality inventory.** One LLM pass over `repos/flanker/` to
   produce the "what does this library actually do" list. Expected buckets:
   *parse a single address*, *parse an address list*, *validate an address
   (syntax / MX / provider plugin)*, *parse a MIME message into a tree*,
   *serialize a MIME tree*, *decode/encode headers*, *detect bounces*, *DKIM
   sign*, *DKIM verify*, *scan/tokenize raw MIME*. This list becomes the unit of
   work and the acceptance checklist.
2. **Focused analysis per item.** Separate LLM call per bucket —
   the article's *"LLMs work better when you limit the amount of thinking."*
   Output per bucket: the files it touches, its public entry point, its current
   test coverage, its Python-2 debt, and its risk class.
3. **Pick a strategy per item** using §10.1 (translation / hybrid /
   reimplementation).
4. **Implement** with the full file-cluster in context, one bucket at a time,
   on a branch per bucket.
5. **Verify integration** — see §10.4.

### 10.4 Verification (generalizing the article's "screenshot" idea)

The article's one concrete verification tactic is for UI: *capture screenshots
of the legacy output and pass them to the LLM so the rewrite matches.* The
non-UI equivalent for flanker is **characterization / golden-master testing**:

- Before any change, run current flanker over a corpus (the existing
  `tests/**` fixtures + a scraped set of real `.eml` files and address lists)
  and **freeze every output** — parsed address tuples, serialized MIME bytes,
  header decodings, bounce verdicts, DKIM results.
- After each bucket's modernization, assert the new output is **byte-identical**
  to the frozen reference. Any intentional difference (e.g. normalizing a
  return convention under the hybrid strategy) is an explicit, reviewed
  exception with its own test.
- This corpus is the objective oracle the article's workflow otherwise lacks,
  and it is what makes "translation-dominant" safe in a security-sensitive
  parser.

### 10.5 Pitfalls the article calls out — and where they bite here

| Article pitfall | Where it shows up in flanker |
| --- | --- |
| Translation carries quirks forward | Inconsistent parser return types; silent `except Exception` in `headers/encoding.py`; the historical `MAX_HEADER_LENGTH` removal. Flag these for hybrid treatment, don't let a mechanical pass cement them. |
| Loss of subtle detail in reimplementation | RFC 5322 quoting/comment handling, MIME charset fallback in `mime/message/fallback/`, DKIM canonicalization. Keep these under translation + golden tests unless there is a strong reason. |
| Analyzing one layer in isolation | De-`six`-ing `address.py` without its `_parser/`, `plugins/`, and `drivers/` collaborators would miss `six.moves.urllib_parse` and `six.text_type` boundary conversions. |
| Over-granular calls lose coherence | Don't de-`six` line-by-line; do it per module-cluster with the bytes/str convention decided once up front. |

### 10.6 Net effect on the roadmap

The GenAI method does not change the **phases** in §7 — it changes *how each
phase is executed*: Phase 0 (nose→pytest) and Phase 1 (drop Py2, remove `six`,
packaging) run as parallel per-module translation sessions gated by the §10.4
golden corpus; Phase 2 (typing) runs the same way; the `WebOb` removal in
Phase 2 and any PLY decision in Phase 3 are the hybrid/reimplementation pieces
that need the requirements-extraction step first.

### 10.7 Run 1 — executed and verified

The Phase 1 "translation" slice has been carried out on a `modernize` branch and
checked against the golden-master corpus. Full write-up: `modernization/RESULTS.md`.

- **Changes** (`+259 / −300` lines, 30 files): `six` removed entirely (19
  modules, ~120 sites); `imghdr` → `flanker/_imagetype.py` (faithful port of
  CPython's recogniser set), `standard-imghdr` pin dropped; `setup.py` →
  `pyproject.toml` with `requires-python = ">=3.9"`; legacy `# coding:` headers
  stripped. Install-time dependency count 13 → 11.
- **Verification** — `harness/characterize.py` exercised 370 address-parse cases
  (strict + lenient), 49 MIME `.eml` trees *including round-trip `to_string()`
  hashes*, 9 bounce cases, plus `parse_list`/URL/header-encoding. Result:

  | baseline @ 3.11 vs modern @ 3.11 | **IDENTICAL** |
  | --- | --- |
  | baseline @ 3.14 vs modern @ 3.14 | **IDENTICAL** |
  | modern @ 3.11 vs modern @ 3.14 | **IDENTICAL** |

- **Finding that sharpened the analysis:** flanker's own `nose` suite could not
  serve as the cross-check — `nose` 1.3.7 fails to import even on Python 3.11
  (`collections.Callable` was removed in 3.10). That is precisely why Phase 0
  (nose→pytest) must come first; here the characterization harness stood in for
  the missing baseline.

---

## Appendix A — How to reproduce this analysis

```bash
# from repos/flanker/
git log --date=format:'%Y' --pretty='%ad' | sort | uniq -c        # commit cadence by year
git for-each-ref --sort=-creatordate --format='%(refname:short) %(creatordate:short)' refs/tags | head
git log --since=2025-01-01 --date=short --pretty='%ad %s'         # the "decay maintenance" commits

find flanker -name '*.py' -not -path '*test*' | wc -l             # library module count
find flanker -name '*.py' | xargs wc -l | tail -1                 # library LOC

grep -rl -E '\bimport six\b|from six' flanker --include='*.py' | grep -vi test | wc -l   # six importers
grep -rho -E '\bsix\.[a-zA-Z_]+' flanker --include='*.py' | grep -vi test | sort | uniq -c | sort -rn
grep -rE 'def .*\) *->' flanker --include='*.py' | grep -vi test | wc -l   # type annotations (0)
grep -rl -E 'coding[:=]' flanker --include='*.py' | wc -l         # legacy encoding headers

grep -rn 'import imghdr' flanker --include='*.py'                 # removed-in-3.13 stdlib module
grep -rn -E 'from nose|import nose|from mock|import mock' tests --include='*.py' | head
cat setup.py .travis.yml tox.ini                                  # packaging + CI
```

## Appendix B — Key files referenced

| File | Why it matters |
| --- | --- |
| `README.rst` | Maintainer disavows the Python 3 build; internal version is `v0.8.5` |
| `CHANGELOG.md` | Last real entry 2019; "only reliable source is the commit log" |
| `setup.py` | Bare packaging; `six` + `standard-imghdr==3.13.0` in `install_requires`; classifiers stop at Py3.6 |
| `.travis.yml` | CI on Python 2.7 + 3.6 only, on a platform defunct for OSS |
| `flanker/_email.py`, `flanker/dkim.py`, `flanker/mime/message/scanner.py` | `six.PY2/PY3` + `six.text_type` branch patterns in hot paths |
| `flanker/mime/message/part.py` | `import imghdr` — removed from stdlib in Python 3.13 |
| `flanker/addresslib/_parser/*_parsetab.py` | Six generated PLY tables committed to the tree |
| `tests/**/*_test.py` | 38 `nose`-based test files; `nose` won't import on Python 3.12+ |

## Appendix C — References

- Diego Garber, *"Modernizing Legacy Software with GenAI: A Practical
  Approach"*, Slalom Build (Medium), 25 Jul 2025 —
  <https://medium.com/slalom-build/modernizing-legacy-software-with-genai-a-practical-approach-2cfc5b67d467>.
  Source of the strategy taxonomy (translation / requirements-extraction /
  hybrid), the parallel-vs-sequential chunking distinction, the complete
  functionality-mapping principle, and the per-functionality workflow applied
  in §10.
- `mailgun/flanker` — <https://github.com/mailgun/flanker> (analyzed at
  `c7f70738`, 2026-04-08).
- Rejected alternative: `ashleysommer/html5lib-modern` —
  <https://github.com/ashleysommer/html5lib-modern> (an existing Python-3
  modernization of html5lib; cited in §2).
