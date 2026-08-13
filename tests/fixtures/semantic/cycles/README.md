# cycles fixture

这个夹具专门检查函数调用图中的 `a -> b -> c -> a` 三节点环和 `self_recursive -> self_recursive` 自环。实现应先识别 SCC，再对缩点后的 DAG 排序；任何一种环都不能让遍历漏掉函数或无限循环。

从 `context-infra` 仓库根目录运行以下命令，使用 `ACCEPTANCE_PROBE.py` 的原始 `enumerate_symbols()` 与本目录清单逐条对账：

```bash
source config/bin_paths.sh
"$PYTHON3_BIN" - "adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer/tests/fixtures/semantic/cycles" <<'PY'
import json
import runpy
import sys
from pathlib import Path

fixture = Path(sys.argv[1])
probe = Path("adhoc_jobs/codebase_explorer_20260321/runs/r002_20260812_semantic_disclosure/design/ACCEPTANCE_PROBE.py")
enumerate_symbols = runpy.run_path(str(probe))["enumerate_symbols"]
actual = list(enumerate_symbols(fixture))
expected = json.loads((fixture / "expected_symbols.json").read_text(encoding="utf-8"))
assert actual == expected, {"actual": actual, "expected": expected}
print(f"PASS: {fixture.name}: {len(actual)} symbols; exact ordered match")
PY
```

核对输出：

```text
PASS: cycles: 4 symbols; exact ordered match
```
