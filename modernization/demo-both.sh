#!/usr/bin/env bash
# Show what flanker does, running on the MODERNIZED library, then prove the
# same script produces byte-identical output on the pristine library and on
# Python 3.14.
#
# Prerequisite: the virtualenvs built by modernization/run.sh
#   (.venv-base, .venv-mod, .venv-mod314)
#
# Run from the project root:  bash modernization/demo-both.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

F="repos/flanker/tests/fixtures"
DEMO="modernization/demo.py"

for v in .venv-base .venv-mod .venv-mod314; do
  [ -x "$v/bin/python" ] || { echo "missing $v -- run: bash modernization/run.sh" >&2; exit 1; }
done

echo "### flanker, running on the MODERNIZED code"
".venv-mod/bin/python" "$DEMO" "$F"

echo
echo "### same script -- pristine vs modernized, Python 3.11 and 3.14 -- must match"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
DEMO_SLOW= ".venv-base/bin/python"    "$DEMO" "$F" >"$tmp/pristine-311" 2>/dev/null
DEMO_SLOW= ".venv-mod/bin/python"     "$DEMO" "$F" >"$tmp/modern-311"   2>/dev/null
DEMO_SLOW= ".venv-mod314/bin/python"  "$DEMO" "$F" >"$tmp/modern-314"   2>/dev/null
diff -q "$tmp/pristine-311" "$tmp/modern-311" >/dev/null && echo "  pristine 3.11  ==  modernized 3.11"
diff -q "$tmp/pristine-311" "$tmp/modern-314" >/dev/null && echo "  pristine 3.11  ==  modernized 3.14"
