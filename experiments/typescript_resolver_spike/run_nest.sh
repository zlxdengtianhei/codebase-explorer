#!/usr/bin/env bash
set -uo pipefail

experiment_dir="$(cd "$(dirname "$0")" && pwd)"
work="$experiment_dir/.work"
results="$experiment_dir/results"
nest="$work/nest"
commit="5df8d9d41a98fd7f587b2e043a12b3d5109971e4"
expected_tree="de9edaba6d249b0a987b7bd191febb13e57d02e9"
expected_root_tree="0c65d58e1d57c762e5ba7017827ecff1e9eb6c81"
mkdir -p "$work" "$results"

if [[ ! -d "$nest/.git" ]]; then
  git clone --filter=blob:none --no-checkout https://github.com/nestjs/nest.git "$nest" > "$results/nest_clone.stdout.txt" 2> "$results/nest_clone.stderr.txt"
  clone_status=$?
  printf '%s\n' "$clone_status" > "$results/nest_clone.exit_code"
  [[ $clone_status -eq 0 ]] || exit "$clone_status"
fi
git -C "$nest" fetch --depth=1 origin "$commit" > "$results/nest_fetch.stdout.txt" 2> "$results/nest_fetch.stderr.txt"
fetch_status=$?
printf '%s\n' "$fetch_status" > "$results/nest_fetch.exit_code"
[[ $fetch_status -eq 0 ]] || exit "$fetch_status"
git -C "$nest" checkout --detach "$commit" > "$results/nest_checkout.stdout.txt" 2> "$results/nest_checkout.stderr.txt"
checkout_status=$?
printf '%s\n' "$checkout_status" > "$results/nest_checkout.exit_code"
[[ $checkout_status -eq 0 ]] || exit "$checkout_status"

actual_commit="$(git -C "$nest" rev-parse HEAD)"
actual_tree="$(git -C "$nest" rev-parse 'HEAD^{tree}')"
actual_root_tree="$(git -C "$nest" rev-parse 'HEAD:packages/core/injector')"
status="mismatch"
if [[ "$actual_commit" == "$commit" && "$actual_tree" == "$expected_tree" && "$actual_root_tree" == "$expected_root_tree" ]]; then status="matched"; fi
printf '{"status":"%s","commit":"%s","tree":"%s","source_root_tree":"%s"}\n' "$status" "$actual_commit" "$actual_tree" "$actual_root_tree" > "$results/nest_revision_check.json"
[[ "$status" == "matched" ]] || exit 3

nest_config="$work/nest.injector.tsconfig.json"
printf '{"compilerOptions":{"target":"ES2022","module":"commonjs","moduleResolution":"node","experimentalDecorators":true,"emitDecoratorMetadata":true,"skipLibCheck":true,"noEmit":true,"baseUrl":"%s"},"include":["%s/packages/core/injector/**/*.ts"]}\n' "$nest" "$nest" > "$nest_config"

/usr/bin/time -l node "$experiment_dir/compiler_probe.mjs" "$nest" "$nest_config" > "$results/compiler_nest_cold.json" 2> "$results/compiler_nest_cold.time.txt"
printf '%s\n' "$?" > "$results/compiler_nest_cold.exit_code"
/usr/bin/time -l node "$experiment_dir/compiler_probe.mjs" "$nest" "$nest_config" > "$results/compiler_nest_warm.json" 2> "$results/compiler_nest_warm.time.txt"
printf '%s\n' "$?" > "$results/compiler_nest_warm.exit_code"

(cd "$nest" && /usr/bin/time -l "$experiment_dir/node_modules/.bin/scip-typescript" index --no-global-caches --output "$results/nest.scip" "$nest_config") > "$results/scip_nest.stdout.txt" 2> "$results/scip_nest.time.txt"
printf '%s\n' "$?" > "$results/scip_nest.exit_code"
if [[ -s "$results/nest.scip" ]]; then
  /usr/bin/time -l node "$experiment_dir/scip_probe.mjs" "$nest" "$results/nest.scip" > "$results/scip_nest.json" 2> "$results/scip_probe_nest.time.txt"
  printf '%s\n' "$?" > "$results/scip_probe_nest.exit_code"
fi
