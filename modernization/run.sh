#!/usr/bin/env bash
# Reproduce modernization run 1: build baseline + modernized flanker in
# matching virtualenvs, characterize both over the corpus, and diff.
#
# Run from the project root:  bash modernization/run.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CORPUS="repos/flanker/tests/fixtures"
HARNESS="modernization/harness/characterize.py"
COMPARE="modernization/harness/compare.py"
mkdir -p modernization/golden

build() {  # <venv-dir> <python> <src>
  uv venv --python "$2" "$1" >/dev/null
  uv pip install --quiet --python "$1/bin/python" -e "$3" >/dev/null
}

echo ">> building baseline (pristine flanker) on 3.11"
build .venv-base 3.11 ./repos/flanker
echo ">> building modernized flanker on 3.11"
build .venv-mod 3.11 ./repos/flanker-modern

echo ">> characterizing"
.venv-base/bin/python "$HARNESS" --corpus "$CORPUS" --out modernization/golden/baseline.json --include-env 2>/dev/null
.venv-mod/bin/python  "$HARNESS" --corpus "$CORPUS" --out modernization/golden/modern.json   --include-env 2>/dev/null

echo ">> comparing"
.venv-base/bin/python "$COMPARE" modernization/golden/baseline.json modernization/golden/modern.json

# Optional 3.14 cross-check (pristine flanker still imports there thanks to
# standard-imghdr + legacy-cgi); comment out if 3.14 is unavailable.
if uv python find 3.14 >/dev/null 2>&1; then
  echo ">> 3.14 cross-check"
  build .venv-base314 3.14 ./repos/flanker
  build .venv-mod314  3.14 ./repos/flanker-modern
  .venv-base314/bin/python "$HARNESS" --corpus "$CORPUS" --out modernization/golden/baseline-py314.json 2>/dev/null
  .venv-mod314/bin/python  "$HARNESS" --corpus "$CORPUS" --out modernization/golden/modern-py314.json   2>/dev/null
  .venv-base/bin/python "$COMPARE" modernization/golden/baseline-py314.json modernization/golden/modern-py314.json
fi

echo ">> done"
