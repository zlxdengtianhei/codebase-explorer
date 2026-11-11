#!/usr/bin/env bash
# Re-record the raw Joern exports used by the no-Joern regression tests.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
PYTHON=${PYTHON:-python3}
JOERN_HOME=${JOERN_HOME:?set JOERN_HOME to the joern-cli directory}
RUN_ROOT=${RUN_ROOT:-$(mktemp -d)}
if [[ -n "${JAVA_HOME:-}" ]]; then export PATH="$JAVA_HOME/bin:$PATH"; fi
export PYTHONPATH="$ROOT/src"
languages=("$@")
if ((${#languages[@]} == 0)); then
  languages=(c cpp python typescript java go ruby)
fi
for language in "${languages[@]}"; do
  CASE="$ROOT/tests/fixtures/graphs/cases/$language" \
  RUN_ROOT="$RUN_ROOT" LANGUAGE="$language" JOERN_HOME="$JOERN_HOME" \
  "$PYTHON" - <<'PY'
import json
import os
from pathlib import Path
from cbe.graph_backends.joern import build_with_joern

case = Path(os.environ["CASE"])
language = os.environ["LANGUAGE"]
run = Path(os.environ["RUN_ROOT"]) / language
result = build_with_joern(case, run, [language], Path(os.environ["JOERN_HOME"]),
                          timeout=600, joern_heap="4g")
if not result["raw"]:
    raise SystemExit(f"no raw export for {language}: {result['diagnostics']}")
payload = result["raw"][0]
payload["_files"] = sorted(payload.get("_files") or ())
text = json.dumps(payload, ensure_ascii=False, indent=2)
text = text.replace(str(case), "<repo>").replace(str(run), "<run>")
path = case / "raw.json"
path.write_text(text + "\n", encoding="utf-8")
if path.stat().st_size > 300_000:
    raise SystemExit(f"{path} exceeds 300 KB")
print(f"recorded {path} ({path.stat().st_size} bytes)")
PY
done
