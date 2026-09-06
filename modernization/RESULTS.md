# Modernization run 1 — results

**Date:** 2026-09-06
**Target:** `mailgun/flanker` @ `c7f7073` → branch `modernize` @ `8733780`
**Method:** §10 of `../CASE_STUDY.md` — translation-dominant modernization with a
golden-master (characterization) corpus as the equivalence oracle.

## Outcome

**The modernized library produces byte-identical output to the pristine library
across the entire `tests/fixtures` corpus, on both Python 3.11 and Python 3.14.**

| Comparison | Result |
| --- | --- |
| baseline @ 3.11  vs  modernized @ 3.11 | **IDENTICAL** |
| baseline @ 3.14  vs  modernized @ 3.14 | **IDENTICAL** |
| modernized @ 3.11  vs  modernized @ 3.14 | **IDENTICAL** |
| baseline @ 3.11  vs  baseline @ 3.14 | **IDENTICAL** |

Corpus exercised by `harness/characterize.py`:

- **370** address-parse cases (`mailbox_valid/invalid.txt`,
  `abridged_localpart_valid/invalid.txt`), each run in both `strict` and lenient
  modes — captures class, `address`, `display_name`, `hostname`, `mailbox`,
  `full_spec`, `requires_non_ascii`, `str()`, and any exception.
- **49** MIME `.eml` fixtures via `mime.from_string` — full recursive part walk
  (content type/disposition/encoding, ordered headers, decoded body sha256,
  child parts) **plus a round-trip `to_string()` sha256** to catch any
  serialization drift.
- **9** bounce fixtures via `msg.bounce` — `is_bounce`, `score`, `status`,
  `notification`, `diagnostic_code`.
- 10 `parse_list` cases (incl. `as_tuple`), URL parsing, header encoding.

The harness is deterministic (no network, no timestamps, sorted keys); two runs
of the same install diff clean.

## What changed

Commit `8733780` — **+259 / −300 lines across 30 files**, no behavior change.

| Change | Detail |
| --- | --- |
| **Removed `six` entirely** | Was imported in 19 modules (~120 call sites). `six.text_type`→`str`, `six.binary_type`→`bytes`, `six.string_types`→`str`, `six.unichr`→`chr`, `six.moves.StringIO`/`six.StringIO`→`io.StringIO`, `six.BytesIO`→`io.BytesIO`, `six.moves.range`→builtin, `six.moves.urllib_parse`→`urllib.parse`, `six.iteritems`/`six.itervalues`→`.items()`/`.values()`, `six.raise_from(e, c)`→`raise e from c`. All `if six.PY2` / `if six.PY3` branches collapsed to the Python 3 arm. |
| **Replaced `imghdr`** | `imghdr` was removed from the stdlib in Python 3.13; flanker had pinned the `standard-imghdr` backport. Now `flanker/_imagetype.py` — a faithful port of CPython `imghdr`'s recogniser set (jpeg/png/gif/tiff/rgb/pbm/pgm/ppm/bmp/webp/exr), same return values. |
| **`setup.py` → `pyproject.toml`** | PEP 621 metadata; `requires-python = ">=3.9"`; `six` and `standard-imghdr` dropped from dependencies; classifiers updated to Python 3.9–3.14, "3 :: Only". |
| **Stripped `# coding:` headers** | 11 files; unnecessary since Python 3. |

Dependency count at install time: **13 → 11** packages (`six`, `standard-imghdr`
gone).

## Notes / limitations

- flanker's **own** test suite (`nose`) could not be used as a cross-check:
  `nose` 1.3.7 fails to import even on Python 3.11 (`AttributeError: module
  'collections' has no attribute 'Callable'`). This is exactly why the
  case study sequences a `nose`→`pytest` port as Phase 0 — the characterization
  harness here stands in for that missing baseline.
- Scope of this run is the "translation-dominant" slice from §10.1. Not yet
  done: type hints (`py.typed`), the `WebOb` dependency audit, PLY-table
  regeneration story. Those are Phases 2/3. (`nose`→`pytest` — Phase 0 — is
  now done; see below.)
- Both `standard-imghdr` and `webob`'s transitive `legacy-cgi` currently keep
  the *un*-modernized flanker importable on Python 3.14, so "won't run on modern
  Python" is too strong for import; the sharper true statements are that the
  **test suite** can't run and the package still ships Python-2 machinery.

---

# Modernization run 2 — `nose` → `pytest` (Phase 0)

**Date:** 2026-09-06
**Target:** branch `modernize` (on top of run 1)

## Outcome

**The test suite runs green on `pytest` on Python 3.11 and 3.14 — the first time
flanker's own tests have executed on a supported interpreter.** Before this,
`nose` 1.3.7 could not even import (`AttributeError: module 'collections' has no
attribute 'Callable'`), so run 1 had to lean entirely on the characterization
harness.

```
255 passed, 6 skipped, 5 xfailed        # identical on CPython 3.11 and 3.14
```

- **6 skipped** — the addresslib plugin tests (`aol`/`gmail`/`google`/`hotmail`/
  `icloud`/`yahoo`) that call `tests.skip_if_asked()`; they hit the live network
  and self-skip unless `pytest --no-skip` is passed.
- **5 xfailed** — pre-existing breakage unrelated to the test-framework port,
  each marked with a reason and left for Phases 2/3:
  `dkim` signing (`RSAPrivateKey.signer()` removed in `cryptography` 3.0),
  `create.guessing_attachments_test` (`email.mime.audio._whatsnd` removed in
  Python 3.11), and two `part` tests whose fixture expectations predate modern
  `chardet` / assume `cchardet`.

## What changed

Test tree + CI only — **no `flanker/` runtime code touched**, so the run 1
golden-master result still holds (re-verified: `IDENTICAL` on the full corpus).

| Change | Detail |
| --- | --- |
| **`nose.tools` asserts → bare `assert`** | 942 call sites across 31 files: `eq_`/`assert_equal`→`assert a == b`, `ok_`/`assert_true`→`assert x`, `assert_false`→`assert not (x)`, `assert_not_equal`, `assert_less`. Operands containing a comparison/boolean operator are parenthesised to avoid accidental chained comparison (e.g. `assert_equal('k' in m, True)` → `assert ('k' in m) == True`). |
| **`nose.tools.assert_raises` → `pytest.raises`** | 11 sites; call form `assert_raises(E, f, x)` → `with pytest.raises(E): f(x)`. |
| **`nose.tools.nottest` → local shim** | `tests/__init__.py` gains a 3-line `nottest` (`func.__test__ = False`); still needed because pytest is configured to collect `*_test` functions and several helpers use that name. |
| **`from nose import SkipTest` → `unittest`** | in `tests/skip_if_asked()`. |
| **`mock` → `unittest.mock`** | the standalone `mock` backport dropped from every test import. |
| **`six` removed from tests** | 9 files (`six.PY2`/`PY3` branches collapsed, `six.text_type`→`str`, `six.moves.StringIO`→`io.StringIO`, `six.unichr`→`chr`). Run 1 had done this for `flanker/` only. |
| **pytest config** | `[tool.pytest.ini_options]` in `pyproject.toml`: `testpaths`, plus `python_files`/`python_functions`/`python_classes` widened to collect the suite's legacy `*_test` naming alongside `test_*`. New root `conftest.py` registers `--no-skip`. |
| **CI** | `.travis.yml` (py2.7/3.6, `nosetests`) → `.github/workflows/ci.yml` (py3.9–3.13 matrix, `pytest`). `tox.ini` envlist + command updated. `HACKING.md` instructions updated. |

Deferred (kept minimal to keep the diff a pure framework port): re-wrapping the
~50 long implicit-string-concat asserts the mechanical pass produced, and
stripping `# coding:` headers from the test files — both belong with the
"add `ruff`" item.

## Reproduce

```bash
cd repos/flanker-modern
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -e '.[tests,validator]' pytest
.venv/bin/pytest -q
```

---

## Reproduce (run 1)

```bash
cd ..                     # project root
bash modernization/run.sh
```

`run.sh` recorded end-to-end (clean rebuild → characterize → diff, ~15s):
[`flanker-golden-master.gif`](flanker-golden-master.gif) ·
[`flanker-golden-master.cast`](flanker-golden-master.cast) (asciicast v2).

For a feature-level view — flanker's address / MIME / bounce API in action on
the modernized code, then shown byte-identical to the pristine library and on
Python 3.14 — see [`demo.py`](demo.py) + [`demo-both.sh`](demo-both.sh)
([`flanker-demo.gif`](flanker-demo.gif) · [`.cast`](flanker-demo.cast)).

or manually:

```bash
uv venv --python 3.11 .venv-base && uv pip install --python .venv-base/bin/python -e ./repos/flanker
uv venv --python 3.11 .venv-mod  && uv pip install --python .venv-mod/bin/python  -e ./repos/flanker-modern
.venv-base/bin/python modernization/harness/characterize.py --corpus repos/flanker/tests/fixtures --out modernization/golden/baseline.json
.venv-mod/bin/python  modernization/harness/characterize.py --corpus repos/flanker/tests/fixtures --out modernization/golden/modern.json
.venv-base/bin/python modernization/harness/compare.py modernization/golden/baseline.json modernization/golden/modern.json
```
