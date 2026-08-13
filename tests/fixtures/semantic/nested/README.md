# nested fixture

这个夹具专门检查作用域链拼接。它同时包含装饰器及其闭包、单行和多行装饰器函数、类中类、方法中的闭包；关键身份包括 `a.py::multiline_decorated`、`a.py::Outer.Inner.method` 和 `a.py::Outer.Inner.method.closure`。多行 `@lru_cache(...)` 用来确认 span 从装饰器首行起算；任何只保留最近一层父级的实现都会漏掉限定名信息。

从 `context-infra` 仓库根目录运行以下命令，使用 `ACCEPTANCE_PROBE.py` 的原始 `enumerate_symbols()` 与本目录清单逐条对账：

```bash
source config/bin_paths.sh
"$PYTHON3_BIN" - "adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer/tests/fixtures/semantic/nested" <<'PY'
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
PASS: nested: 8 symbols; exact ordered match
```
