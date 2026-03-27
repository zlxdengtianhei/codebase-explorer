"""E2E pipeline test: validates the V2 analysis pipeline end-to-end.

Tests the full stack WITHOUT MCP transport -- calls core functions directly
using an AST-based fallback parser (since graph-sitter/codegen cannot be
imported in the current environment).

Pipeline under test:
  1. AST fallback -> CodebaseSnapshot (with char_count)
  2. build_weighted_dependency_graph -> WeightedGraphResult
  3. extract_feature_cones -> {cone_id: FeatureCone}, infrastructure set
  4. estimate_tokens_from_chars -> int per file
  5. calculate_feature_cone_depth -> depth per cone
  6. build_task_manifest -> FFD task manifest dict
  7. atomic_write_state / read_state / update_task_status -> state management
  8. [Bug check] server.py analyze_codebase attribute issues

Extended tests (T-07):
  9. Dependency graph tests (Mermaid generation, scope=project/file)
  10. Feature cone tests (cone fields, infrastructure sharing)
  11. Index Agent protocol validation (SKILL.md Phase 4/5 variables)
  12. Task manifest bin-packing tests (batch/single/split types)

Usage:
    .venv/bin/python -m pytest tests/test_e2e_pipeline.py -v
    .venv/bin/python tests/test_e2e_pipeline.py
"""
from __future__ import annotations

import ast as _ast
import json
import logging
import re
import sys
import tempfile
from pathlib import Path

import pytest

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
SRC_ROOT = _PROJECT_ROOT / "src"

SKILL_MD_PATH = _PROJECT_ROOT / ".agents" / "skills" / "codebase-explorer" / "SKILL.md"


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
# Determine test root: prefer Flask, fallback to project's own src/
# ---------------------------------------------------------------------------


def _select_test_root() -> Path:
    """Select the test target root directory.

    Returns Flask src/flask if available, otherwise the project's own src/.
    """
    if FLASK_ROOT.exists() and any(FLASK_ROOT.rglob("*.py")):
        return FLASK_ROOT
    return SRC_ROOT


TEST_ROOT = _select_test_root()


# ---------------------------------------------------------------------------
# Full pipeline runner
# ---------------------------------------------------------------------------


def _run_pipeline(root: Path) -> dict:
    log.info("Step 1: AST parse -> snapshot")
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

    log.info("Step 4: Estimate tokens (chars / ratio)")
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
# Shared fixtures (avoid re-running pipeline per test)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline_result():
    """Run the full pipeline once per test module and share the result."""
    return _run_pipeline(TEST_ROOT)


@pytest.fixture(scope="module")
def analysis_output_dir(tmp_path_factory, pipeline_result):
    """Write analysis JSON files to a temporary directory (once per module).

    Returns the output dir Path and the written JSON data dict.
    """
    import hashlib
    from datetime import UTC, datetime

    result = pipeline_result
    snap = result["snapshot"]
    weighted = result["weighted"]
    cones = result["cones"]
    cone_dicts = result["cone_dicts"]
    file_tokens = result["file_tokens"]
    manifest = result["manifest"]
    infra = result["infrastructure"]

    output_dir = tmp_path_factory.mktemp("codebase_analysis")
    project_id = hashlib.sha256(str(TEST_ROOT).encode()).hexdigest()[:12]
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
            "project_id": project_id, "path": str(TEST_ROOT),
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
                {
                    "source": u, "target": v,
                    "weight": weighted.graph[u][v].get("weight", 1),
                    "edge_types": weighted.graph[u][v].get("edge_types", []),
                }
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
                {
                    "filepath": fp,
                    "language": "python",
                    "char_count": next(
                        (fi.char_count for fi in snap.files if fi.filepath == fp), 0
                    ),
                    "line_count": next(
                        (fi.line_count for fi in snap.files if fi.filepath == fp), 0
                    ),
                    "estimated_tokens": tok,
                    "method": "chars",
                }
                for fp, tok in file_tokens.items()
            ],
        },
        "05_task_manifest.json": manifest,
    }

    for fname, data in outputs.items():
        fpath = output_dir / fname
        fpath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
        )

    return output_dir


# ---------------------------------------------------------------------------
# Original tests (updated to use TEST_ROOT instead of FLASK_ROOT)
# ---------------------------------------------------------------------------


class TestCoreDataModels:
    """Test basic data model correctness."""

    def test_fileinfo_has_char_count(self):
        """FileInfo must expose char_count (needed by estimator and server)."""
        fi = FileInfo(
            filepath="x.py", language="python", line_count=10,
            char_count=500, function_names=(), class_names=(), import_sources=(),
        )
        assert fi.char_count == 500
        log.info("PASS: FileInfo has char_count")

    def test_server_api_signature_consistent(self):
        """Verify server.py API is consistent with the fixed data models.

        Checks:
        - parser.FileInfo has char_count (needed by server analyze_codebase)
        - estimate_tokens_from_chars returns int (server stores it directly)
        """
        from src.parser.codebase import FileInfo as ParserFileInfo

        fi_fields = set(ParserFileInfo.__dataclass_fields__.keys())
        assert "char_count" in fi_fields, (
            "parser.FileInfo is missing 'char_count' -- server.py will AttributeError"
        )

        result = estimate_tokens_from_chars(1000, "python")
        assert isinstance(result, int), (
            f"estimate_tokens_from_chars should return int, got {type(result)}"
        )
        assert result > 0, "Token estimate for 1000 chars must be > 0"
        log.info("PASS: server API signatures are consistent")


class TestASTParser:
    """Test AST-based snapshot building."""

    def test_ast_snapshot_produces_files(self):
        """AST parser must produce >=5 files from test source."""
        snap = _ast_build_snapshot(TEST_ROOT)
        assert len(snap.files) >= 5, f"Expected >=5 files, got {len(snap.files)}"
        assert len(snap.functions) >= 5, f"Expected >=5 functions, got {len(snap.functions)}"
        assert snap.total_lines >= 100
        log.info("PASS: snapshot has %d files", len(snap.files))


class TestWeightedGraph:
    """Test weighted dependency graph construction."""

    def test_weighted_graph_has_nodes_and_edges(self, pipeline_result):
        """Weighted graph must have nodes and edges."""
        result = pipeline_result["weighted"]
        assert result.node_count > 0, "Graph has no nodes"
        assert result.edge_count >= 0, "edge_count must be non-negative"
        assert result.total_weight >= 0
        log.info("PASS: graph has %d nodes, %d edges", result.node_count, result.edge_count)


class TestFeatureCones:
    """Test feature cone extraction."""

    def test_feature_cones_extracted(self, pipeline_result):
        """At least 1 feature cone must be extracted."""
        cones = pipeline_result["cones"]
        assert len(cones) >= 1, f"Expected >=1 cone, got {len(cones)}"
        log.info("PASS: %d cones extracted", len(cones))

    def test_cone_files_are_known_paths(self, pipeline_result):
        """Every file in every cone must come from the parsed snapshot."""
        snap = pipeline_result["snapshot"]
        all_fps = {fi.filepath for fi in snap.files}
        cones = pipeline_result["cones"]
        for cone_id, cone in cones.items():
            for fp in cone.exclusive_files:
                assert fp in all_fps, f"Cone '{cone_id}' has unknown file: {fp}"
        log.info("PASS: all cone files are valid")


class TestTokenEstimation:
    """Test token estimation."""

    def test_token_estimates_positive(self, pipeline_result):
        """Token estimates must be non-negative for all files."""
        snap = pipeline_result["snapshot"]
        for fi in snap.files:
            tokens = estimate_tokens_from_chars(fi.char_count, fi.language)
            assert tokens >= 0, f"Negative tokens for {fi.filepath}: {tokens}"
        log.info("PASS: all token estimates non-negative")


class TestDepthCalculation:
    """Test cone depth calculation."""

    def test_depth_values_in_range(self, pipeline_result):
        """Cone depth must be in [0, 5]."""
        for cone_id, depth in pipeline_result["depths"].items():
            assert 0 <= depth <= 5, f"Cone '{cone_id}' depth={depth} out of [0,5]"
        log.info("PASS: all depths in [0, 5]")


class TestTaskManifest:
    """Test task manifest construction."""

    def test_task_manifest_schema(self, pipeline_result):
        """Manifest must have schema_version='2.0' and >=1 task."""
        manifest = pipeline_result["manifest"]
        assert manifest.get("schema_version") == "2.0", (
            f"Expected '2.0', got {manifest.get('schema_version')!r}"
        )
        tasks = manifest.get("tasks", {})
        assert len(tasks) >= 1, "Manifest must have >=1 task"
        log.info("PASS: manifest has %d tasks, schema_version='2.0'", len(tasks))

    def test_task_types_valid(self, pipeline_result):
        """Every task must have a valid type (single, batch, split, or index)."""
        valid_types = {"single", "batch", "split", "index"}
        for task_id, task in pipeline_result["manifest"].get("tasks", {}).items():
            assert task.get("type") in valid_types, (
                f"Task '{task_id}' has bad type: {task.get('type')!r}"
            )
        log.info("PASS: all task types are valid")

    def test_task_cone_ids_reference_real_cones(self, pipeline_result):
        """cone_ids in tasks must all be real cone IDs (or 'all' for index tasks)."""
        valid = set(pipeline_result["cones"].keys())
        for task_id, task in pipeline_result["manifest"].get("tasks", {}).items():
            for cid in task.get("cone_ids", []):
                if cid == "all":
                    assert task.get("type") == "index", (
                        f"Task '{task_id}' uses cone_id='all' but type is not 'index'"
                    )
                    continue
                assert cid in valid, f"Task '{task_id}' references unknown cone: '{cid}'"
        log.info("PASS: all task cone_ids valid")


class TestCoverage:
    """Test file coverage."""

    def test_coverage_of_source_files(self, pipeline_result):
        """Most files should be covered by cones or infrastructure (>=50%)."""
        result = pipeline_result
        all_fps = {fi.filepath for fi in result["snapshot"].files}
        covered: set[str] = set(result["infrastructure"])
        for cone in result["cones"].values():
            covered.update(cone.exclusive_files)
            covered.update(cone.shared_deps)
        pct = len(covered & all_fps) / len(all_fps) * 100 if all_fps else 100.0
        log.info("Coverage: %.1f%% (%d/%d files)", pct, len(covered & all_fps), len(all_fps))
        assert pct >= 50.0, f"Coverage too low: {pct:.1f}%"
        log.info("PASS: coverage=%.1f%%", pct)


class TestStateManagement:
    """Test state management round-trips."""

    def test_state_management(self, tmp_path):
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


class TestJSONOutput:
    """Test JSON file generation."""

    def test_pipeline_writes_five_json_files(self, analysis_output_dir):
        """Full pipeline writes 5 valid JSON output files."""
        output_dir = analysis_output_dir

        required_files = [
            "01_structure.json",
            "02_dag.json",
            "03_feature_cones.json",
            "04_file_tokens.json",
            "05_task_manifest.json",
        ]

        for fname in required_files:
            fpath = output_dir / fname
            assert fpath.exists(), f"Missing: {fname}"
            parsed = json.loads(fpath.read_text())
            assert isinstance(parsed, dict), f"{fname} is not a dict"

        # Spot-check content
        structure = json.loads((output_dir / "01_structure.json").read_text())
        assert structure["file_count"] >= 5
        assert structure["total_lines"] >= 100

        cones_json = json.loads((output_dir / "03_feature_cones.json").read_text())
        assert cones_json["cone_count"] >= 1

        manifest_json = json.loads((output_dir / "05_task_manifest.json").read_text())
        assert manifest_json["schema_version"] == "2.0"
        assert len(manifest_json["tasks"]) >= 1

        log.info("PASS: 5 JSON files written and validated")


# ===========================================================================
# T-07 NEW TESTS: Dependency Graph, Feature Cones, Index Protocol, Task Packing
# ===========================================================================


class TestDependencyGraph:
    """Test dependency graph generation including Mermaid rendering."""

    def test_project_scope_mermaid_non_empty(self, pipeline_result):
        """get_dependency_graph(scope='project') returns non-empty Mermaid graph."""
        import networkx as nx
        from src.server import _build_graph_from_dag, _render_mermaid

        weighted = pipeline_result["weighted"]

        # Simulate the server-side rendering path
        nodes = list(weighted.graph.nodes())
        edges = [
            {
                "source": u, "target": v,
                "weight": weighted.graph[u][v].get("weight", 1),
                "edge_types": weighted.graph[u][v].get("edge_types", []),
            }
            for u, v in weighted.graph.edges()
        ]

        graph = _build_graph_from_dag(nodes, edges)
        mermaid = _render_mermaid(graph)

        assert mermaid is not None, "Mermaid output is None"
        assert len(mermaid) > 0, "Mermaid output is empty"

        # Must contain "graph" or "flowchart" keyword
        mermaid_lower = mermaid.lower()
        assert "graph" in mermaid_lower or "flowchart" in mermaid_lower, (
            f"Mermaid output does not contain 'graph' or 'flowchart': {mermaid[:200]}"
        )
        log.info("PASS: project scope Mermaid graph contains valid keyword")

    def test_project_scope_mermaid_has_nodes(self, pipeline_result):
        """Project-scope Mermaid diagram must define at least one node."""
        from src.server import _build_graph_from_dag, _render_mermaid

        weighted = pipeline_result["weighted"]
        nodes = list(weighted.graph.nodes())
        edges = [
            {
                "source": u, "target": v,
                "weight": weighted.graph[u][v].get("weight", 1),
            }
            for u, v in weighted.graph.edges()
        ]

        graph = _build_graph_from_dag(nodes, edges)
        mermaid = _render_mermaid(graph)

        # Node definitions look like: n0["label"]
        node_pattern = re.compile(r'n\d+\["[^"]+"\]')
        matches = node_pattern.findall(mermaid)
        assert len(matches) >= 1, (
            f"Mermaid diagram has no node definitions. Output:\n{mermaid[:500]}"
        )
        log.info("PASS: Mermaid diagram has %d node definitions", len(matches))

    def test_file_scope_subgraph(self, pipeline_result):
        """get_dependency_graph(scope='file', target=<known_file>) returns neighbor subgraph."""
        from src.server import _build_graph_from_dag, _render_mermaid

        weighted = pipeline_result["weighted"]
        nodes = list(weighted.graph.nodes())
        edges = [
            {
                "source": u, "target": v,
                "weight": weighted.graph[u][v].get("weight", 1),
                "edge_types": weighted.graph[u][v].get("edge_types", []),
            }
            for u, v in weighted.graph.edges()
        ]

        graph = _build_graph_from_dag(nodes, edges)

        # Pick a known file that has at least one edge (use a file with edges)
        target_file = None
        for node in graph.nodes():
            if graph.degree(node) > 0:
                target_file = node
                break

        if target_file is None:
            pytest.skip("No file with edges in graph; cannot test file-scope subgraph")

        # Build N-hop neighbor subgraph (mimicking server logic)
        nodes_to_include = {target_file}
        frontier = {target_file}
        for _ in range(1):  # 1-hop
            new_frontier = set()
            for node in frontier:
                new_frontier.update(graph.predecessors(node))
                new_frontier.update(graph.successors(node))
            nodes_to_include.update(new_frontier)
            frontier = new_frontier

        subgraph = graph.subgraph(nodes_to_include).copy()
        mermaid = _render_mermaid(subgraph)

        # Subgraph must contain the target file
        assert subgraph.number_of_nodes() >= 1, "File subgraph has no nodes"
        assert target_file in subgraph, "Target file not in subgraph"

        # Mermaid must be non-empty
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower(), (
            f"File-scope Mermaid missing graph keyword: {mermaid[:200]}"
        )
        log.info(
            "PASS: file-scope subgraph for '%s' has %d nodes",
            target_file, subgraph.number_of_nodes(),
        )

    def test_mermaid_with_weights(self, pipeline_result):
        """Mermaid rendering with include_weights=True includes weight annotations."""
        from src.server import _build_graph_from_dag, _render_mermaid

        weighted = pipeline_result["weighted"]
        nodes = list(weighted.graph.nodes())
        edges = [
            {
                "source": u, "target": v,
                "weight": weighted.graph[u][v].get("weight", 1),
                "edge_types": weighted.graph[u][v].get("edge_types", []),
            }
            for u, v in weighted.graph.edges()
        ]

        graph = _build_graph_from_dag(nodes, edges)
        mermaid = _render_mermaid(graph, include_weights=True)

        if weighted.edge_count > 0:
            # Weight annotations look like: -->|type w=N|
            assert "w=" in mermaid, (
                f"Weighted Mermaid missing 'w=' annotation: {mermaid[:300]}"
            )
        log.info("PASS: Mermaid with weights renders correctly")

    def test_circular_deps_detected(self, pipeline_result):
        """Circular dependency detection returns a list (possibly empty)."""
        import networkx as nx

        graph = pipeline_result["weighted"].graph
        circular = [
            sorted(scc)
            for scc in nx.strongly_connected_components(graph)
            if len(scc) > 1
        ]
        # Just verify it is a list; project may or may not have circular deps
        assert isinstance(circular, list), "circular_deps is not a list"
        log.info("PASS: circular deps detection returned %d groups", len(circular))


class TestFeatureConesExtended:
    """Extended feature cone tests (T-07 requirement #2)."""

    def test_get_feature_cones_returns_list(self, pipeline_result):
        """get_feature_cones() returns a dict of feature cones."""
        cones = pipeline_result["cones"]
        assert isinstance(cones, dict), "cones is not a dict"
        assert len(cones) >= 1, f"Expected >=1 cone, got {len(cones)}"
        log.info("PASS: feature cones returned as dict with %d entries", len(cones))

    def test_cone_has_required_fields(self, pipeline_result):
        """Each cone must contain exclusive_files, entry_point fields."""
        cones = pipeline_result["cones"]
        for cone_id, cone in cones.items():
            assert hasattr(cone, "exclusive_files"), (
                f"Cone '{cone_id}' missing exclusive_files"
            )
            assert hasattr(cone, "entry_point"), (
                f"Cone '{cone_id}' missing entry_point"
            )
            assert hasattr(cone, "cone_id"), (
                f"Cone '{cone_id}' missing cone_id"
            )
            # exclusive_files must be a list
            assert isinstance(cone.exclusive_files, list), (
                f"Cone '{cone_id}' exclusive_files is not a list"
            )
            # entry_point must be a non-empty string
            assert isinstance(cone.entry_point, str) and len(cone.entry_point) > 0, (
                f"Cone '{cone_id}' has empty or non-string entry_point"
            )
        log.info("PASS: all cones have required fields")

    def test_cone_dicts_have_required_fields(self, pipeline_result):
        """Cone dicts (as used in task manifest) must have expected keys."""
        cone_dicts = pipeline_result["cone_dicts"]
        required_keys = {"cone_id", "entry_point", "exclusive_files", "shared_deps", "layer", "token_count"}
        for cone_id, cd in cone_dicts.items():
            missing = required_keys - set(cd.keys())
            assert not missing, (
                f"Cone dict '{cone_id}' missing keys: {missing}"
            )
        log.info("PASS: all cone_dicts have required keys")

    def test_minimum_cone_count(self, pipeline_result):
        """At least 3 feature cones must be extracted from the test codebase."""
        cones = pipeline_result["cones"]
        assert len(cones) >= 3, (
            f"Expected >=3 cones from test codebase, got {len(cones)}"
        )
        log.info("PASS: %d cones >= 3", len(cones))

    def test_infrastructure_nodes_are_shared(self, pipeline_result):
        """Infrastructure nodes must be files shared by multiple cones."""
        cones = pipeline_result["cones"]
        infrastructure = pipeline_result["infrastructure"]

        if not infrastructure:
            # Infrastructure can be empty for very simple codebases
            log.info("SKIP: no infrastructure nodes detected (acceptable for small codebases)")
            return

        # Verify each infrastructure file appears in shared_deps of >= 2 cones
        for infra_file in infrastructure:
            cone_refs = sum(
                1 for cone in cones.values()
                if infra_file in cone.shared_deps
            )
            assert cone_refs >= 2, (
                f"Infrastructure file '{infra_file}' is shared by only {cone_refs} cone(s), "
                f"expected >=2"
            )
        log.info(
            "PASS: %d infrastructure files are all shared by >=2 cones",
            len(infrastructure),
        )


class TestIndexAgentProtocol:
    """Test Index Agent protocol validation (T-07 requirement #3).

    Validates that SKILL.md Phase 4/5 prompt templates reference variables
    that correspond to actual JSON fields in the analysis output.
    """

    @pytest.fixture(scope="class")
    def skill_md_content(self):
        """Read SKILL.md content once for the class."""
        if not SKILL_MD_PATH.exists():
            pytest.skip(f"SKILL.md not found at {SKILL_MD_PATH}")
        return SKILL_MD_PATH.read_text(encoding="utf-8")

    def test_phase4_index_agent_prompt_exists(self, skill_md_content):
        """Phase 4 INDEX Agent Prompt Template must exist in SKILL.md."""
        assert "Phase 4" in skill_md_content, (
            "SKILL.md does not mention Phase 4"
        )
        assert "INDEX Agent" in skill_md_content, (
            "SKILL.md does not mention INDEX Agent"
        )
        assert "INDEX Agent Prompt Template" in skill_md_content, (
            "SKILL.md does not contain INDEX Agent Prompt Template section"
        )
        log.info("PASS: Phase 4 INDEX Agent Prompt Template found in SKILL.md")

    def test_phase4_feature_cones_variable(self, skill_md_content):
        """Phase 4 prompt must reference {{feature_cones_json}} variable."""
        assert "{{feature_cones_json}}" in skill_md_content, (
            "SKILL.md Phase 4 prompt missing {{feature_cones_json}} variable"
        )
        log.info("PASS: {{feature_cones_json}} variable found")

    def test_phase4_snippet_content_variable(self, skill_md_content):
        """Phase 4 prompt must reference snippet content variable."""
        assert "{{snippet_content}}" in skill_md_content, (
            "SKILL.md Phase 4 prompt missing {{snippet_content}} variable"
        )
        log.info("PASS: {{snippet_content}} variable found")

    def test_phase4_task_manifest_variable(self, skill_md_content):
        """Phase 4 prompt must reference {{task_manifest_json}} variable."""
        assert "{{task_manifest_json}}" in skill_md_content, (
            "SKILL.md Phase 4 prompt missing {{task_manifest_json}} variable"
        )
        log.info("PASS: {{task_manifest_json}} variable found")

    def test_phase4_file_tokens_variable(self, skill_md_content):
        """Phase 4 prompt must reference {{file_tokens_json}} variable."""
        assert "{{file_tokens_json}}" in skill_md_content, (
            "SKILL.md Phase 4 prompt missing {{file_tokens_json}} variable"
        )
        log.info("PASS: {{file_tokens_json}} variable found")

    def test_phase4_project_id_variable(self, skill_md_content):
        """Phase 4 doc-manifest.json schema must include {{project_id}}."""
        assert "{{project_id}}" in skill_md_content, (
            "SKILL.md Phase 4 doc-manifest schema missing {{project_id}} variable"
        )
        log.info("PASS: {{project_id}} variable found in doc-manifest schema")

    def test_phase5_reorganization_prompt_exists(self, skill_md_content):
        """Phase 5 Reorganization Prompt must exist in SKILL.md."""
        assert "Phase 5" in skill_md_content, (
            "SKILL.md does not mention Phase 5"
        )
        assert "Semantic Reorganization" in skill_md_content, (
            "SKILL.md does not mention Semantic Reorganization"
        )
        assert "Reorganization INDEX Agent" in skill_md_content, (
            "SKILL.md does not contain Reorganization INDEX Agent section"
        )
        log.info("PASS: Phase 5 Reorganization Prompt found in SKILL.md")

    def test_phase5_unit_rule_exists(self, skill_md_content):
        """Phase 5 must contain @unit rules."""
        assert "@unit" in skill_md_content, (
            "SKILL.md Phase 5 missing @unit rules"
        )
        # Verify @unit parsing regex is defined
        assert "UNIT_PATTERN" in skill_md_content or "@unit:" in skill_md_content, (
            "SKILL.md missing @unit parsing pattern definition"
        )
        log.info("PASS: @unit rules found in SKILL.md")

    def test_phase5_unit_regex_pattern(self, skill_md_content):
        """Phase 5 must define the @unit regex pattern for parsing."""
        assert "<!-- @unit:" in skill_md_content, (
            "SKILL.md missing <!-- @unit: --> marker definition"
        )
        assert "<!-- @/unit:" in skill_md_content, (
            "SKILL.md missing <!-- @/unit: --> closing marker definition"
        )
        log.info("PASS: @unit marker syntax defined in SKILL.md")

    def test_doc_manifest_schema_defined(self, skill_md_content):
        """doc-manifest.json Schema must be defined in SKILL.md."""
        assert "doc-manifest.json" in skill_md_content, (
            "SKILL.md does not reference doc-manifest.json"
        )
        # Schema must include key fields
        assert '"details"' in skill_md_content, (
            "doc-manifest.json schema missing 'details' field"
        )
        assert '"groups"' in skill_md_content, (
            "doc-manifest.json schema missing 'groups' field"
        )
        assert '"version"' in skill_md_content, (
            "doc-manifest.json schema missing 'version' field"
        )
        assert '"operations_log"' in skill_md_content, (
            "doc-manifest.json schema missing 'operations_log' field"
        )
        log.info("PASS: doc-manifest.json schema defined in SKILL.md")

    def test_phase4_variables_match_json_fields(
        self, skill_md_content, pipeline_result,
    ):
        """Verify Phase 4 prompt variables correspond to actual JSON field names.

        The INDEX Agent prompt references {{feature_cones_json}}, {{snippet_content}},
        {{task_manifest_json}}, and {{file_tokens_json}}. These should map to data
        produced by the analysis pipeline.
        """
        # feature_cones_json -> maps to 03_feature_cones.json content
        cone_dicts = pipeline_result["cone_dicts"]
        for cd in cone_dicts.values():
            assert "exclusive_files" in cd, "cone data missing exclusive_files"
            assert "entry_point" in cd, "cone data missing entry_point"

        # snippet_content -> will be generated by DETAIL Agents (validated structurally)
        # Prompt references {{cone_name}} and {{cone_id}} -- verify cones have IDs
        for cone_id, cone in pipeline_result["cones"].items():
            assert cone.cone_id == cone_id, (
                f"Cone '{cone_id}' has mismatched cone_id: {cone.cone_id}"
            )

        # task_manifest_json -> maps to 05_task_manifest.json
        manifest = pipeline_result["manifest"]
        assert "tasks" in manifest, "manifest missing 'tasks' key"
        assert "schema_version" in manifest, "manifest missing 'schema_version' key"

        # file_tokens_json -> maps to 04_file_tokens.json
        file_tokens = pipeline_result["file_tokens"]
        assert len(file_tokens) > 0, "file_tokens is empty"

        log.info("PASS: Phase 4 template variables match actual JSON fields")

    def test_phase5_reorganization_variables_table(self, skill_md_content):
        """Phase 5 Template Variable Injection Reference table must exist."""
        assert "Template Variable Injection Reference" in skill_md_content, (
            "SKILL.md missing Template Variable Injection Reference table"
        )
        # Verify key variables are in the reference table
        expected_vars = [
            "{{group_name}}",
            "{{group_id}}",
            "{{current_manifest}}",
            "{{detail_id}}",
            "{{tokens}}",
        ]
        for var in expected_vars:
            assert var in skill_md_content, (
                f"Phase 5 variable reference table missing {var}"
            )
        log.info("PASS: Phase 5 variable injection reference table validated")

    def test_doc_manifest_status_transitions(self, skill_md_content):
        """SKILL.md must define doc-manifest status transitions: initial -> final."""
        assert '"initial"' in skill_md_content, (
            "SKILL.md missing 'initial' status for doc-manifest"
        )
        assert '"final"' in skill_md_content, (
            "SKILL.md missing 'final' status for doc-manifest"
        )
        assert '"reorganizing"' in skill_md_content, (
            "SKILL.md missing 'reorganizing' intermediate status"
        )
        log.info("PASS: doc-manifest status transitions defined (initial -> reorganizing -> final)")


class TestTaskBinPacking:
    """Test task manifest bin-packing (T-07 requirement #4)."""

    def test_task_manifest_exists_and_valid(self, pipeline_result):
        """Task manifest from pipeline must exist and be a valid dict."""
        manifest = pipeline_result["manifest"]
        assert isinstance(manifest, dict), "manifest is not a dict"
        assert "tasks" in manifest, "manifest missing 'tasks' key"
        assert "schema_version" in manifest, "manifest missing 'schema_version'"
        assert manifest["schema_version"] == "2.0", (
            f"Unexpected schema_version: {manifest['schema_version']}"
        )
        log.info("PASS: task manifest is valid")

    def test_task_manifest_has_multiple_tasks(self, pipeline_result):
        """Task manifest must contain >= 2 tasks (at least 1 detail + 1 index)."""
        tasks = pipeline_result["manifest"].get("tasks", {})
        assert len(tasks) >= 2, (
            f"Expected >=2 tasks (detail + index), got {len(tasks)}"
        )
        log.info("PASS: task manifest has %d tasks", len(tasks))

    def test_task_types_include_at_least_two_kinds(self, pipeline_result):
        """Task types must include at least 2 of {batch, single, split, index}."""
        tasks = pipeline_result["manifest"].get("tasks", {})
        observed_types = {task.get("type") for task in tasks.values()}
        assert len(observed_types) >= 2, (
            f"Expected >=2 task types, got {observed_types}"
        )
        log.info("PASS: task types include %s", observed_types)

    def test_index_task_exists(self, pipeline_result):
        """An 'index' type task must exist in the manifest."""
        tasks = pipeline_result["manifest"].get("tasks", {})
        index_tasks = [t for t in tasks.values() if t.get("type") == "index"]
        assert len(index_tasks) >= 1, "No index task found in manifest"
        log.info("PASS: index task found")

    def test_index_task_depends_on_all_detail_tasks(self, pipeline_result):
        """The index task must depend on all non-index tasks."""
        tasks = pipeline_result["manifest"].get("tasks", {})
        index_tasks = [t for t in tasks.values() if t.get("type") == "index"]
        assert len(index_tasks) >= 1, "No index task found"

        index_task = index_tasks[0]
        detail_task_ids = sorted(
            tid for tid, t in tasks.items() if t.get("type") != "index"
        )
        index_deps = sorted(index_task.get("dependencies", []))

        assert index_deps == detail_task_ids, (
            f"Index task dependencies {index_deps} != detail task IDs {detail_task_ids}"
        )
        log.info("PASS: index task depends on all %d detail tasks", len(detail_task_ids))

    def test_each_task_has_required_fields(self, pipeline_result):
        """Every task must have required fields: task_id, type, cone_ids, files, status."""
        required_fields = {"task_id", "type", "cone_ids", "status"}
        tasks = pipeline_result["manifest"].get("tasks", {})
        for task_id, task in tasks.items():
            missing = required_fields - set(task.keys())
            assert not missing, (
                f"Task '{task_id}' missing required fields: {missing}"
            )
        log.info("PASS: all tasks have required fields")

    def test_task_tokens_within_budget(self, pipeline_result):
        """No task should exceed the context budget."""
        manifest = pipeline_result["manifest"]
        budget = manifest.get("context_budget", 100_000)
        tasks = manifest.get("tasks", {})
        for task_id, task in tasks.items():
            total = task.get("total_tokens", 0)
            assert total <= budget, (
                f"Task '{task_id}' total_tokens={total} exceeds budget={budget}"
            )
        log.info("PASS: all tasks within token budget")

    def test_all_cones_assigned_to_tasks(self, pipeline_result):
        """Every non-infrastructure cone must appear in at least one task."""
        cone_ids = set(pipeline_result["cones"].keys())
        tasks = pipeline_result["manifest"].get("tasks", {})

        assigned_cones: set[str] = set()
        for task in tasks.values():
            for cid in task.get("cone_ids", []):
                if cid != "all":
                    assigned_cones.add(cid)

        unassigned = cone_ids - assigned_cones
        assert not unassigned, (
            f"Cones not assigned to any task: {unassigned}"
        )
        log.info("PASS: all %d cones assigned to tasks", len(cone_ids))


class TestJSONFileIntegrity:
    """Test that JSON output files have consistent cross-references."""

    def test_dag_nodes_match_structure_files(self, analysis_output_dir):
        """02_dag.json nodes should be a subset of 01_structure.json files."""
        structure = json.loads(
            (analysis_output_dir / "01_structure.json").read_text(),
        )
        dag = json.loads(
            (analysis_output_dir / "02_dag.json").read_text(),
        )
        structure_files = {f["filepath"] for f in structure["files"]}
        dag_nodes = set(dag["nodes"])

        extra_nodes = dag_nodes - structure_files
        assert not extra_nodes, (
            f"DAG has nodes not in structure: {extra_nodes}"
        )
        log.info("PASS: DAG nodes are subset of structure files")

    def test_cone_files_exist_in_structure(self, analysis_output_dir):
        """03_feature_cones.json exclusive_files should appear in 01_structure.json."""
        structure = json.loads(
            (analysis_output_dir / "01_structure.json").read_text(),
        )
        cones = json.loads(
            (analysis_output_dir / "03_feature_cones.json").read_text(),
        )
        structure_files = {f["filepath"] for f in structure["files"]}

        for cone_id, cone_data in cones["cones"].items():
            for fp in cone_data.get("exclusive_files", []):
                assert fp in structure_files, (
                    f"Cone '{cone_id}' exclusive_file '{fp}' not in structure"
                )
        log.info("PASS: all cone files found in structure")

    def test_token_files_match_structure(self, analysis_output_dir):
        """04_file_tokens.json files should match 01_structure.json files."""
        structure = json.loads(
            (analysis_output_dir / "01_structure.json").read_text(),
        )
        tokens = json.loads(
            (analysis_output_dir / "04_file_tokens.json").read_text(),
        )
        structure_files = {f["filepath"] for f in structure["files"]}
        token_files = {f["filepath"] for f in tokens["files"]}

        assert token_files == structure_files, (
            f"Token files mismatch. Extra in tokens: {token_files - structure_files}. "
            f"Missing from tokens: {structure_files - token_files}"
        )
        log.info("PASS: token files match structure files")

    def test_manifest_cone_ids_exist_in_cones(self, analysis_output_dir):
        """05_task_manifest.json cone_ids should reference 03_feature_cones.json cones."""
        cones = json.loads(
            (analysis_output_dir / "03_feature_cones.json").read_text(),
        )
        manifest = json.loads(
            (analysis_output_dir / "05_task_manifest.json").read_text(),
        )
        valid_cone_ids = set(cones["cones"].keys())

        for task_id, task in manifest["tasks"].items():
            for cid in task.get("cone_ids", []):
                if cid == "all":
                    continue
                assert cid in valid_cone_ids, (
                    f"Task '{task_id}' references unknown cone '{cid}'"
                )
        log.info("PASS: all manifest cone_ids reference valid cones")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_standalone():
    tests_no_tmp = [
        ("TestCoreDataModels.fileinfo_has_char_count",
         TestCoreDataModels().test_fileinfo_has_char_count),
        ("TestCoreDataModels.server_api_signature_consistent",
         TestCoreDataModels().test_server_api_signature_consistent),
        ("TestASTParser.ast_snapshot_produces_files",
         TestASTParser().test_ast_snapshot_produces_files),
    ]

    passed = failed = 0
    failures: list[tuple[str, str]] = []

    def _run(name, fn, *args):
        nonlocal passed, failed
        try:
            fn(*args)
            print(f"  PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
            failures.append((name, str(e)))
        except Exception as e:
            print(f"  FAIL {name}: ERROR: {e}")
            failed += 1
            failures.append((name, f"ERROR: {e}"))

    print(f"\n-- Core tests (no pipeline) -----------")
    for name, fn in tests_no_tmp:
        _run(name, fn)

    print(f"\n-- Pipeline tests ----------------------")
    try:
        result = _run_pipeline(TEST_ROOT)
        print(f"  Pipeline ran successfully with {len(result['cones'])} cones")
    except Exception as e:
        print(f"  FAIL Pipeline: {e}")
        failed += 1
        failures.append(("Pipeline", str(e)))

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if failures:
        print("\nFailed:")
        for name, msg in failures:
            print(f"  - {name}:\n    {msg}\n")
    return failed == 0


if __name__ == "__main__":
    print(f"Test root: {TEST_ROOT}")
    if not TEST_ROOT.exists():
        print(f"ERROR: not found: {TEST_ROOT}")
        sys.exit(1)
    ok = _run_standalone()
    sys.exit(0 if ok else 1)
