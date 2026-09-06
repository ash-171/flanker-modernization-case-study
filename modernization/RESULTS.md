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
  done: `nose`→`pytest` port, type hints (`py.typed`), the `WebOb` dependency
  audit, PLY-table regeneration story. Those are Phases 0/2/3.
- Both `standard-imghdr` and `webob`'s transitive `legacy-cgi` currently keep
  the *un*-modernized flanker importable on Python 3.14, so "won't run on modern
  Python" is too strong for import; the sharper true statements are that the
  **test suite** can't run and the package still ships Python-2 machinery.

## Reproduce

```bash
cd ..                     # project root
bash modernization/run.sh
```

or manually:

```bash
uv venv --python 3.11 .venv-base && uv pip install --python .venv-base/bin/python -e ./repos/flanker
uv venv --python 3.11 .venv-mod  && uv pip install --python .venv-mod/bin/python  -e ./repos/flanker-modern
.venv-base/bin/python modernization/harness/characterize.py --corpus repos/flanker/tests/fixtures --out modernization/golden/baseline.json
.venv-mod/bin/python  modernization/harness/characterize.py --corpus repos/flanker/tests/fixtures --out modernization/golden/modern.json
.venv-base/bin/python modernization/harness/compare.py modernization/golden/baseline.json modernization/golden/modern.json
```
