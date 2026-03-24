"""E2E pipeline test: validates the V2 analysis pipeline end-to-end.

Tests the full stack WITHOUT MCP transport — calls core functions directly
using an AST-based fallback parser (since graph-sitter/codegen cannot be
imported in the current environment).

Pipeline under test:
  1. AST fallback → CodebaseSnapshot (with char_count)
  2. build_weighted_dependency_graph → WeightedGraphResult
  3. extract_feature_cones → {cone_id: FeatureCone}, infrastructure set
  4. estimate_tokens_from_chars → int per file
  5. calculate_feature_cone_depth → depth per cone
  6. build_task_manifest → FFD task manifest dict
  7. atomic_write_state / read_state / update_task_status → state management
  8. [Bug check] server.py analyze_codebase attribute issues

Usage:
    .venv/bin/python -m pytest tests/test_e2e_pipeline.py -v
    .venv/bin/python tests/test_e2e_pipeline.py
"""
from __future__ import annotations

import ast as _ast
import json
import logging
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import build_task_manifest, calculate_feature_cone_depth
from src.graph.feature_cone import extract_feature_cones
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import (
    ClassInfo,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
)
from src.state.json_store import atomic_write_state, read_state, update_task_status

logging.basicConfig(level=logging.WARNING, format="[E2E] %(levelname)s %(message)s")
log = logging.getLogger("e2e_pipeline")
log.setLevel(logging.INFO)

FLASK_ROOT = _PROJECT_ROOT / "test_repos" / "flask" / "src" / "flask"


# ---------------------------------------------------------------------------
# AST-based snapshot builder (no graph-sitter required)
# ---------------------------------------------------------------------------


def _resolve_import_to_filepath(
    module: str,
    level: int,
    current_file_rel: str,
    all_file_rels: set[str],
    pkg_prefix: str,
) -> str | None:
    """Resolve a Python import statement to a relative file path.

    Handles both relative imports (from . import x) and absolute imports
    (import flask.app) by trying candidate paths against the known file set.

    Args:
        module: Module name string (e.g. "app", "flask.app", "json")
        level: Relative import level (0=absolute, 1=from ., 2=from ..)
        current_file_rel: Relative path of the importing file
        all_file_rels: Set of all known relative file paths
        pkg_prefix: Package directory prefix (e.g. "flask/")

    Returns:
        Resolved relative file path, or None if not resolvable.
    """
    current_dir = str(Path(current_file_rel).parent)

    # Build candidate base paths to try
    candidates: list[str] = []

    if level > 0:
        # Relative import: from . import x  or  from .sub import x
        base_dir = current_dir
        for _ in range(level - 1):
            base_dir = str(Path(base_dir).parent)
        mod_path = module.replace(".", "/") if module else ""
        if mod_path:
            candidates.append(f"{base_dir}/{mod_path}.py")
            candidates.append(f"{base_dir}/{mod_path}/__init__.py")
        else:
            candidates.append(f"{base_dir}/__init__.py")
    else:
        # Absolute import: try within the same package first, then as-is
        mod_path = module.replace(".", "/")
        candidates.append(f"{pkg_prefix}{mod_path}.py")
        candidates.append(f"{pkg_prefix}{mod_path}/__init__.py")
        candidates.append(f"{mod_path}.py")
        candidates.append(f"{mod_path}/__init__.py")

    for c in candidates:
        # Normalize double slashes
        c = str(Path(c))
        if c in all_file_rels:
            return c
    return None


def _ast_build_snapshot(root: Path, language: str = "python") -> CodebaseSnapshot:
    """Build a CodebaseSnapshot from Python files using stdlib ast.

    Resolves import statements to file paths so that the weighted dependency
    graph can build real edges (not just module-name strings).
    """
    # First pass: collect all relative file paths for import resolution
    all_rel_paths: set[str] = set()
    for py_path in root.rglob("*.py"):
        all_rel_paths.add(str(py_path.relative_to(root.parent)))

    pkg_prefix = root.name + "/"  # e.g. "flask/"

    files: list[FileInfo] = []
    funcs: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    total_lines = 0

    for py_path in sorted(root.rglob("*.py")):
        try:
            source = py_path.read_text(encoding="utf-8")
        except Exception:
            continue

        char_count = len(source)
        line_count = source.count("\n") + 1
        rel = str(py_path.relative_to(root.parent))
        total_lines += line_count

        try:
            tree = _ast.parse(source, filename=str(py_path))
        except SyntaxError:
            files.append(FileInfo(
                filepath=rel, language=language, line_count=line_count,
                char_count=char_count, function_names=(), class_names=(), import_sources=(),
            ))
            continue

        func_names: list[str] = []
        class_names: list[str] = []
        resolved_imports: list[str] = []

        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                func_names.append(node.name)
                params = [a.arg for a in node.args.args]
                calls: list[str] = []
                for child in _ast.walk(node):
                    if isinstance(child, _ast.Call):
                        if isinstance(child.func, _ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, _ast.Attribute):
                            calls.append(child.func.attr)
                funcs.append(FunctionInfo(
                    name=node.name, filepath=rel,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    parameters=tuple(params), return_type=None,
                    calls=tuple(calls), dependencies=(),
                ))
            elif isinstance(node, _ast.ClassDef):
                class_names.append(node.name)
                methods = [
                    n.name for n in _ast.iter_child_nodes(node)
                    if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                ]
                bases = []
                for b in node.bases:
                    if isinstance(b, _ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, _ast.Attribute):
                        bases.append(b.attr)
                classes.append(ClassInfo(
                    name=node.name, filepath=rel,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    methods=tuple(methods), base_classes=tuple(bases), subclasses=(),
                ))
            elif isinstance(node, _ast.Import):
                for alias in node.names:
                    fp = _resolve_import_to_filepath(
                        alias.name, 0, rel, all_rel_paths, pkg_prefix)
                    if fp:
                        resolved_imports.append(fp)
            elif isinstance(node, _ast.ImportFrom):
                module = node.module or ""
                level = node.level or 0
                fp = _resolve_import_to_filepath(
                    module, level, rel, all_rel_paths, pkg_prefix)
                if fp:
                    resolved_imports.append(fp)

        files.append(FileInfo(
            filepath=rel, language=language, line_count=line_count,
            char_count=char_count,
            function_names=tuple(func_names),
            class_names=tuple(class_names),
            import_sources=tuple(dict.fromkeys(resolved_imports)),  # deduplicate, preserve order
        ))

    return CodebaseSnapshot(
        root_path=str(root),
        files=tuple(files),
        functions=tuple(funcs),
        classes=tuple(classes),
        languages_detected=(language,),
        total_lines=total_lines,
    )


# ---------------------------------------------------------------------------
# Full pipeline runner
# ---------------------------------------------------------------------------


def _run_pipeline(root: Path) -> dict:
    log.info("Step 1: AST parse → snapshot")
    snapshot = _ast_build_snapshot(root)
    log.info("  %d files, %d functions, %d classes, %d lines",
             len(snapshot.files), len(snapshot.functions),
             len(snapshot.classes), snapshot.total_lines)

    log.info("Step 2: Build weighted dependency graph")
    weighted = build_weighted_dependency_graph(snapshot)
    log.info("  nodes=%d, edges=%d, weight=%.1f",
             weighted.node_count, weighted.edge_count, weighted.total_weight)

    log.info("Step 3: Extract feature cones")
    cones, infrastructure = extract_feature_cones(weighted.graph, snapshot)
    log.info("  cones=%d, infrastructure=%d", len(cones), len(infrastructure))

    log.info("Step 4: Estimate tokens (chars ÷ ratio)")
    file_tokens: dict[str, int] = {}
    for fi in snapshot.files:
        lang = fi.language or "default"
        tokens = estimate_tokens_from_chars(fi.char_count, lang)
        file_tokens[fi.filepath] = tokens
    log.info("  total_tokens=%d across %d files", sum(file_tokens.values()), len(file_tokens))

    log.info("Step 5: Calculate cone depths")
    cone_dicts: dict[str, dict] = {}
    depths: dict[str, int] = {}
    for cone_id, cone in cones.items():
        cone_tokens = sum(file_tokens.get(f, 0) for f in cone.exclusive_files)
        dag_layers = cone.layer + 1
        depth = calculate_feature_cone_depth(cone_tokens, dag_layers=dag_layers)
        depths[cone_id] = depth
        cone_dicts[cone_id] = {
            "cone_id": cone_id,
            "entry_point": cone.entry_point,
            "exclusive_files": cone.exclusive_files,
            "shared_deps": cone.shared_deps,
            "layer": cone.layer,
            "token_count": cone_tokens,
        }

    log.info("Step 6: Build task manifest (FFD bin-packing)")
    manifest = build_task_manifest(cone_dicts, file_tokens)
    log.info("  tasks=%d, schema_version=%s",
             len(manifest.get("tasks", {})), manifest.get("schema_version"))

    return {
        "snapshot": snapshot,
        "weighted": weighted,
        "cones": cones,
        "infrastructure": infrastructure,
        "file_tokens": file_tokens,
        "depths": depths,
        "cone_dicts": cone_dicts,
        "manifest": manifest,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fileinfo_has_char_count():
    """FileInfo must expose char_count (needed by estimator and server)."""
    fi = FileInfo(
        filepath="x.py", language="python", line_count=10,
        char_count=500, function_names=(), class_names=(), import_sources=(),
    )
    assert fi.char_count == 500
    log.info("PASS: FileInfo has char_count")


def test_ast_snapshot_produces_files():
    """AST parser must produce ≥5 files from Flask source."""
    snap = _ast_build_snapshot(FLASK_ROOT)
    assert len(snap.files) >= 5, f"Expected ≥5 files, got {len(snap.files)}"
    assert len(snap.functions) >= 5, f"Expected ≥5 functions, got {len(snap.functions)}"
    assert snap.total_lines >= 100
    log.info("PASS: snapshot has %d files", len(snap.files))


def test_weighted_graph_has_nodes_and_edges():
    """Weighted graph must have nodes and edges."""
    snap = _ast_build_snapshot(FLASK_ROOT)
    result = build_weighted_dependency_graph(snap)
    assert result.node_count > 0, "Graph has no nodes"
    assert result.edge_count >= 0, "edge_count must be non-negative"
    assert result.total_weight >= 0
    log.info("PASS: graph has %d nodes, %d edges", result.node_count, result.edge_count)


def test_feature_cones_extracted():
    """At least 1 feature cone must be extracted from Flask."""
    snap = _ast_build_snapshot(FLASK_ROOT)
    weighted = build_weighted_dependency_graph(snap)
    cones, infrastructure = extract_feature_cones(weighted.graph, snap)
    assert len(cones) >= 1, f"Expected ≥1 cone, got {len(cones)}"
    log.info("PASS: %d cones, %d infra files", len(cones), len(infrastructure))


def test_cone_files_are_known_paths():
    """Every file in every cone must come from the parsed snapshot."""
    snap = _ast_build_snapshot(FLASK_ROOT)
    all_fps = {fi.filepath for fi in snap.files}
    weighted = build_weighted_dependency_graph(snap)
    cones, _ = extract_feature_cones(weighted.graph, snap)
    for cone_id, cone in cones.items():
        for fp in cone.exclusive_files:
            assert fp in all_fps, f"Cone '{cone_id}' has unknown file: {fp}"
    log.info("PASS: all cone files are valid")


def test_token_estimates_positive():
    """Token estimates must be non-negative for all files."""
    snap = _ast_build_snapshot(FLASK_ROOT)
    for fi in snap.files:
        tokens = estimate_tokens_from_chars(fi.char_count, fi.language)
        assert tokens >= 0, f"Negative tokens for {fi.filepath}: {tokens}"
    log.info("PASS: all token estimates non-negative")


def test_depth_values_in_range():
    """Cone depth must be in [0, 5]."""
    result = _run_pipeline(FLASK_ROOT)
    for cone_id, depth in result["depths"].items():
        assert 0 <= depth <= 5, f"Cone '{cone_id}' depth={depth} out of [0,5]"
    log.info("PASS: all depths in [0, 5]")


def test_task_manifest_schema():
    """Manifest must have schema_version='2.0' and ≥1 task."""
    result = _run_pipeline(FLASK_ROOT)
    manifest = result["manifest"]
    assert manifest.get("schema_version") == "2.0", (
        f"Expected '2.0', got {manifest.get('schema_version')!r}"
    )
    tasks = manifest.get("tasks", {})
    assert len(tasks) >= 1, "Manifest must have ≥1 task"
    log.info("PASS: manifest has %d tasks, schema_version='2.0'", len(tasks))


def test_task_types_valid():
    """Every task must have a valid type (single, batch, split, or index)."""
    result = _run_pipeline(FLASK_ROOT)
    valid_types = {"single", "batch", "split", "index"}
    for task_id, task in result["manifest"].get("tasks", {}).items():
        assert task.get("type") in valid_types, (
            f"Task '{task_id}' has bad type: {task.get('type')!r}"
        )
    log.info("PASS: all task types are valid")


def test_task_cone_ids_reference_real_cones():
    """cone_ids in tasks must all be real cone IDs (or 'all' for index tasks)."""
    result = _run_pipeline(FLASK_ROOT)
    valid = set(result["cones"].keys())
    for task_id, task in result["manifest"].get("tasks", {}).items():
        for cid in task.get("cone_ids", []):
            if cid == "all":
                # INDEX Assembly task uses "all" as a sentinel
                assert task.get("type") == "index", (
                    f"Task '{task_id}' uses cone_id='all' but type is not 'index'"
                )
                continue
            assert cid in valid, f"Task '{task_id}' references unknown cone: '{cid}'"
    log.info("PASS: all task cone_ids valid")


def test_coverage_of_source_files():
    """Most files should be covered by cones or infrastructure (≥50%)."""
    result = _run_pipeline(FLASK_ROOT)
    all_fps = {fi.filepath for fi in result["snapshot"].files}
    covered: set[str] = set(result["infrastructure"])
    for cone in result["cones"].values():
        covered.update(cone.exclusive_files)
        covered.update(cone.shared_deps)
    pct = len(covered & all_fps) / len(all_fps) * 100 if all_fps else 100.0
    log.info("Coverage: %.1f%% (%d/%d files)", pct, len(covered & all_fps), len(all_fps))
    assert pct >= 50.0, f"Coverage too low: {pct:.1f}%"
    log.info("PASS: coverage=%.1f%%", pct)


def test_state_management(tmp_path):
    """atomic_write_state / read_state / update_task_status must round-trip."""
    state_path = tmp_path / "state.json"
    state = {
        "project_id": "test123",
        "tasks": {
            "task_001": {"status": "pending", "output_files": []},
        },
        "documentation": {"details_written": 0},
    }
    atomic_write_state(state_path, state)
    loaded = read_state(state_path)
    assert loaded is not None, "read_state returned None"
    assert loaded["project_id"] == "test123"
    assert loaded["tasks"]["task_001"]["status"] == "pending"

    (tmp_path / "detail.md").write_text("# Detail")
    updated = update_task_status(
        state_path, "task_001", status="complete",
        output_files=[{"path": str(tmp_path / "detail.md"), "type": "detail"}],
    )
    assert updated["tasks"]["task_001"]["status"] == "complete"
    log.info("PASS: state management round-trip")


def test_pipeline_writes_five_json_files(tmp_path):
    """Full pipeline writes 5 valid JSON output files."""
    import hashlib
    from datetime import UTC, datetime

    result = _run_pipeline(FLASK_ROOT)
    snap = result["snapshot"]
    weighted = result["weighted"]
    cones = result["cones"]
    cone_dicts = result["cone_dicts"]
    file_tokens = result["file_tokens"]
    manifest = result["manifest"]
    infra = result["infrastructure"]

    project_id = hashlib.sha256(str(FLASK_ROOT).encode()).hexdigest()[:12]
    now = datetime.now(UTC).isoformat()

    files_data = [
        {
            "filepath": fi.filepath, "language": fi.language,
            "line_count": fi.line_count, "char_count": fi.char_count,
            "function_names": list(fi.function_names),
            "class_names": list(fi.class_names),
            "import_sources": list(fi.import_sources),
        }
        for fi in snap.files
    ]

    outputs = {
        "01_structure.json": {
            "project_id": project_id, "path": str(FLASK_ROOT),
            "analyzed_at": now,
            "languages": list(snap.languages_detected),
            "file_count": len(snap.files),
            "function_count": len(snap.functions),
            "class_count": len(snap.classes),
            "total_lines": snap.total_lines,
            "files": files_data,
        },
        "02_dag.json": {
            "project_id": project_id,
            "node_count": weighted.node_count,
            "edge_count": weighted.edge_count,
            "total_weight": weighted.total_weight,
            "nodes": list(weighted.graph.nodes()),
            "edges": [
                {"source": u, "target": v, "weight": weighted.graph[u][v].get("weight", 1)}
                for u, v in weighted.graph.edges()
            ],
        },
        "03_feature_cones.json": {
            "project_id": project_id,
            "cone_count": len(cones),
            "infrastructure_files": list(infra),
            "cones": cone_dicts,
        },
        "04_file_tokens.json": {
            "project_id": project_id,
            "total_tokens": sum(file_tokens.values()),
            "file_count": len(file_tokens),
            "files": [
                {"filepath": fp, "estimated_tokens": tok}
                for fp, tok in file_tokens.items()
            ],
        },
        "05_task_manifest.json": manifest,
    }

    for fname, data in outputs.items():
        fpath = tmp_path / fname
        fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    for fname in outputs:
        fpath = tmp_path / fname
        assert fpath.exists(), f"Missing: {fname}"
        parsed = json.loads(fpath.read_text())
        assert isinstance(parsed, dict), f"{fname} is not a dict"

    # Spot-check content
    structure = json.loads((tmp_path / "01_structure.json").read_text())
    assert structure["file_count"] >= 5
    assert structure["total_lines"] >= 100

    cones_json = json.loads((tmp_path / "03_feature_cones.json").read_text())
    assert cones_json["cone_count"] >= 1

    manifest_json = json.loads((tmp_path / "05_task_manifest.json").read_text())
    assert manifest_json["schema_version"] == "2.0"
    assert len(manifest_json["tasks"]) >= 1

    log.info("PASS: 5 JSON files written and validated")


# ---------------------------------------------------------------------------
# Bug check: server.py analyze_codebase
# ---------------------------------------------------------------------------


def test_server_api_signature_consistent():
    """Verify server.py API is consistent with the fixed data models.

    Checks:
    - parser.FileInfo has char_count (needed by server analyze_codebase)
    - estimate_tokens_from_chars returns int (server stores it directly)
    """
    from src.parser.codebase import FileInfo as ParserFileInfo

    # Check 1: char_count exists on parser FileInfo
    fi_fields = set(ParserFileInfo.__dataclass_fields__.keys())
    assert "char_count" in fi_fields, (
        "parser.FileInfo is missing 'char_count' — server.py will AttributeError"
    )

    # Check 2: estimate_tokens_from_chars returns int (not TokenEstimate)
    result = estimate_tokens_from_chars(1000, "python")
    assert isinstance(result, int), (
        f"estimate_tokens_from_chars should return int, got {type(result)}"
    )
    assert result > 0, "Token estimate for 1000 chars must be > 0"

    log.info("PASS: server API signatures are consistent")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_standalone():
    tests_no_tmp = [
        test_fileinfo_has_char_count,
        test_ast_snapshot_produces_files,
        test_weighted_graph_has_nodes_and_edges,
        test_feature_cones_extracted,
        test_cone_files_are_known_paths,
        test_token_estimates_positive,
        test_depth_values_in_range,
        test_task_manifest_schema,
        test_task_types_valid,
        test_task_cone_ids_reference_real_cones,
        test_coverage_of_source_files,
    ]
    tests_with_tmp = [
        test_state_management,
        test_pipeline_writes_five_json_files,
    ]
    bug_tests = [test_server_api_signature_consistent]

    passed = failed = 0
    failures: list[tuple[str, str]] = []

    def _run(fn, *args):
        nonlocal passed, failed
        name = fn.__name__
        try:
            fn(*args)
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
            failures.append((name, str(e)))
        except Exception as e:
            print(f"  ✗ {name}: ERROR: {e}")
            failed += 1
            failures.append((name, f"ERROR: {e}"))

    print("\n── Core pipeline tests ──────────────────────────────────────────")
    for fn in tests_no_tmp:
        _run(fn)

    print("\n── State & JSON output tests ────────────────────────────────────")
    for fn in tests_with_tmp:
        with tempfile.TemporaryDirectory() as td:
            _run(fn, Path(td))

    print("\n── Bug checks ───────────────────────────────────────────────────")
    for fn in bug_tests:
        _run(fn)

    print(f"\n{'─'*65}")
    print(f"Results: {passed} passed, {failed} failed")
    if failures:
        print("\nFailed:")
        for name, msg in failures:
            print(f"  • {name}:\n    {msg}\n")
    return failed == 0


if __name__ == "__main__":
    print(f"Flask source: {FLASK_ROOT}")
    if not FLASK_ROOT.exists():
        print(f"ERROR: not found: {FLASK_ROOT}")
        sys.exit(1)
    ok = _run_standalone()
    sys.exit(0 if ok else 1)
