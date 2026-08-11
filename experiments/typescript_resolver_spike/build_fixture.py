from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_fixture.py ORACLE_JSON OUTPUT_ROOT")
    oracle_path = Path(sys.argv[1]).resolve()
    output_root = Path(sys.argv[2]).resolve()
    contract = json.loads(oracle_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []
    for relative, record in contract["files"].items():
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(record["content_lines"])
        if record["trailing_newline"]:
            content += "\n"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        expected = record["content_sha256"]
        if digest != expected:
            raise RuntimeError(f"oracle reconstruction mismatch: {relative}: {digest} != {expected}")
        target.write_text(content, encoding="utf-8", newline="")
        checks.append({"path": relative, "sha256": digest, "matched": True})
    tsconfig = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "CommonJS",
            "moduleResolution": "Node",
            "strict": True,
            "noEmit": True,
            "skipLibCheck": True,
        },
        "include": ["src/**/*.ts"],
        "exclude": ["vendor", "generated"],
    }
    (output_root / "tsconfig.json").write_text(
        json.dumps(tsconfig, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"oracle": str(oracle_path), "root": str(output_root), "files": checks}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
