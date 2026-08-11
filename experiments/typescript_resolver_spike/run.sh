#!/usr/bin/env bash
set -uo pipefail

experiment_dir="$(cd "$(dirname "$0")" && pwd)"
impl_dir="$(cd "$experiment_dir/../.." && pwd)"
repo_root="$(cd "$impl_dir/../../../.." && pwd)"
oracle="$impl_dir/tests/oracles/contracts/typescript/expected_ir.json"
lock="$impl_dir/tests/real/oracles.lock.json"
work="$experiment_dir/.work"
results="$experiment_dir/results"
fixture="$work/fixture"
mkdir -p "$work" "$results"

python_bin="$impl_dir/.venv/bin/python"
"$python_bin" "$experiment_dir/build_fixture.py" "$oracle" "$fixture" > "$results/fixture_reconstruction.json"

(cd "$experiment_dir" && npm install --ignore-scripts --no-audit --no-fund) > "$results/npm_install.stdout.txt" 2> "$results/npm_install.stderr.txt"
npm_status=$?
printf '%s\n' "$npm_status" > "$results/npm_install.exit_code"

if [[ $npm_status -eq 0 ]]; then
  /usr/bin/time -l node "$experiment_dir/compiler_probe.mjs" "$fixture" "$fixture/tsconfig.json" > "$results/compiler_fixture_cold.json" 2> "$results/compiler_fixture_cold.time.txt"
  printf '%s\n' "$?" > "$results/compiler_fixture_cold.exit_code"
  /usr/bin/time -l node "$experiment_dir/compiler_probe.mjs" "$fixture" "$fixture/tsconfig.json" > "$results/compiler_fixture_warm.json" 2> "$results/compiler_fixture_warm.time.txt"
  printf '%s\n' "$?" > "$results/compiler_fixture_warm.exit_code"

  (cd "$fixture" && /usr/bin/time -l "$experiment_dir/node_modules/.bin/scip-typescript" index --infer-tsconfig --output "$results/fixture.scip") > "$results/scip_fixture.stdout.txt" 2> "$results/scip_fixture.time.txt"
  printf '%s\n' "$?" > "$results/scip_fixture.exit_code"
  /usr/bin/time -l node "$experiment_dir/scip_probe.mjs" "$fixture" "$results/fixture.scip" > "$results/scip_fixture.json" 2> "$results/scip_probe_fixture.time.txt"
  printf '%s\n' "$?" > "$results/scip_probe_fixture.exit_code"
fi

/usr/bin/time -l "$python_bin" "$experiment_dir/graph_sitter_probe.py" "$fixture" > "$results/graph_sitter_fixture.json" 2> "$results/graph_sitter_fixture.time.txt"
printf '%s\n' "$?" > "$results/graph_sitter_fixture.exit_code"

"$python_bin" - "$lock" > "$results/nest_lock.json" <<'PY'
import json, sys
lock=json.load(open(sys.argv[1], encoding='utf-8'))['repositories']['nest_core_injector']
print(json.dumps(lock, indent=2, sort_keys=True))
PY

if [[ -f "$experiment_dir/package-lock.json" ]]; then
  "$python_bin" "$experiment_dir/collect_supply_chain.py" "$experiment_dir" > "$results/supply_chain.json"
fi

printf '%s\n' "run complete; Nest checkout and bounded project probes are executed separately by run_nest.sh"
