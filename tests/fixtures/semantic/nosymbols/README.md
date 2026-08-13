# nosymbols fixture

这个夹具专门检查文件级终态，而不是 symbol 数量。空 `__init__.py`、只有常量的文件、只有模块级语句的文件和故意带语法错误的 `broken.py` 都没有可枚举 symbol，但四个 `.py` 文件仍必须进入文件分母并得到明确终态，不能被静默跳过。`broken.py` 的语法错误是夹具内容，不应修复。

从 `context-infra` 仓库根目录运行以下命令，使用 `ACCEPTANCE_PROBE.py` 的原始 `enumerate_symbols()` 与本目录清单逐条对账：

```bash
source config/bin_paths.sh
"$PYTHON3_BIN" - "adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer/tests/fixtures/semantic/nosymbols" <<'PY'
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
PASS: nosymbols: 0 symbols; exact ordered match
```
