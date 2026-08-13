# dupnames fixture

这个夹具专门检查限定名身份：五个 `__init__`、三个 `run` 和两个模块级 `shared` 分布在三个文件中。若实现用裸函数名作为节点键，这 15 个 symbol 组成的集合会发生错误折叠；正确实现应保留路径、类作用域和函数名组成的完整身份。

从 `context-infra` 仓库根目录运行以下命令，使用 `ACCEPTANCE_PROBE.py` 的原始 `enumerate_symbols()` 与本目录清单逐条对账：

```bash
source config/bin_paths.sh
"$PYTHON3_BIN" - "adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer/tests/fixtures/semantic/dupnames" <<'PY'
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
PASS: dupnames: 15 symbols; exact ordered match
```
