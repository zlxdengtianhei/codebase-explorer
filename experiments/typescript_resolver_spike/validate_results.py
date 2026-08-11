from __future__ import annotations

import json
import sys
from pathlib import Path


FACTS = ("ts.type.runner.run", "ts.implements.worker", "ts.call.worker.run")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    experiment = Path(sys.argv[1]).resolve()
    oracle_path = Path(sys.argv[2]).resolve()
    results = experiment / "results"
    oracle = load(oracle_path)["expected_facts"]
    compiler = load(results / "compiler_fixture_cold.json")
    compiler_warm = load(results / "compiler_fixture_warm.json")
    scip = load(results / "scip_fixture.json")
    graph = load(results / "graph_sitter_fixture.json")
    nest_revision = load(results / "nest_revision_check.json")
    nest_compiler = load(results / "compiler_nest_cold.json")
    nest_scip = load(results / "scip_nest.json")
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    for fact_id in FACTS:
        expected = oracle[fact_id]
        actual = compiler["facts"][fact_id]
        check(f"compiler:{fact_id}:observed", actual["observed"], actual)
        check(f"compiler:{fact_id}:span", actual["span"] == {"path": expected["path"], **expected["span"]}, actual["span"])
        check(f"compiler-warm:{fact_id}:stable", compiler_warm["facts"][fact_id] == actual, compiler_warm["facts"][fact_id])
    check("compiler:type-target", compiler["facts"][FACTS[0]]["target"] == "string", compiler["facts"][FACTS[0]]["target"])
    impl_target = compiler["facts"][FACTS[1]]["target"]
    call_target = compiler["facts"][FACTS[2]]["target"]
    check("compiler:implements-target", impl_target["path"] == "src/base.ts" and impl_target["name"].endswith(".Runner"), impl_target)
    check("compiler:call-target", call_target["path"] == "src/base.ts" and call_target["name"].endswith(".Runner.run"), call_target)
    check("compiler:receiver-type", compiler["facts"][FACTS[2]]["receiver_type"] == "Runner", compiler["facts"][FACTS[2]]["receiver_type"])
    check("compiler:expected-diagnostics-only", {item["code"] for item in compiler["diagnostics"]} == {1110, 2304}, compiler["diagnostics"])

    check("scip:three-locations-observed", all(scip["facts"][item]["observed"] for item in FACTS), scip["facts"])
    check("scip:type-doc-string-only", "documentation string" in scip["facts"][FACTS[0]]["evidence_surface"], scip["facts"][FACTS[0]])
    check("scip:no-explicit-implements-edge", "no implements edge" in scip["facts"][FACTS[1]]["evidence_surface"], scip["facts"][FACTS[1]])
    check("scip:no-explicit-call-edge", "not an explicit call edge" in scip["facts"][FACTS[2]]["evidence_surface"], scip["facts"][FACTS[2]])

    check("graph-sitter:unmodified-import-fails", graph["unmodified_import"]["status"] == "incompatible", graph["unmodified_import"])
    check("graph-sitter:no-three-facts", not any(graph["facts"][item]["observed"] for item in FACTS), graph["facts"])
    check("nest:locked-revision", nest_revision["status"] == "matched", nest_revision)
    check("nest:bounded-compiler-roots", nest_compiler["root_file_count"] == 30, nest_compiler["root_file_count"])
    check("nest:bounded-scip-documents", nest_scip["document_count"] == 30, nest_scip["document_count"])
    check("nest:dependency-degradation-visible", nest_compiler["diagnostic_count"] > 0, nest_compiler["diagnostic_count"])

    passed = all(item["passed"] for item in checks)
    print(json.dumps({"status": "pass" if passed else "fail", "check_count": len(checks), "checks": checks}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
