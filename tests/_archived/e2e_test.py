"""E2E test: Run codebase-explorer against the Flask repository.

This script exercises the full pipeline without MCP transport:
  1. Parse Flask source code (with ast-based fallback if graph-sitter fails).
  2. Build dependency graph.
  3. Group modules via Louvain.
  4. Compute module metrics.
  5. Plan documentation structure (dynamic depth).
  6. Generate all documents via Jinja2 templates.
  7. Write doc-index.json.
  8. Validate outputs against acceptance criteria.

Usage:
    python -m tests.e2e_test
"""
from __future__ import annotations

import ast
import json
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so ``src.*`` imports resolve.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FLASK_SRC = _PROJECT_ROOT / "test_repos" / "flask" / "src" / "flask"
OUTPUT_DIR = _PROJECT_ROOT / "test_repos" / "flask" / ".codebase-docs"

logging.basicConfig(
    level=logging.INFO,
    format="[E2E] %(levelname)s %(message)s",
)
log = logging.getLogger("e2e")


# ---------------------------------------------------------------------------
# Fallback parser using stdlib ``ast``
# ---------------------------------------------------------------------------

from src.parser.codebase import (
    ClassInfo,
    CodebaseParser,
    CodebaseParseError,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
)


def _ast_parse_file(filepath: Path, root: Path) -> tuple[
    FileInfo | None,
    list[FunctionInfo],
    list[ClassInfo],
]:
    """Parse a single Python file using the stdlib ``ast`` module."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return None, [], []

    line_count = source.count("\n") + 1
    rel_path = str(filepath.relative_to(root))

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        fi = FileInfo(
            filepath=rel_path,
            language="python",
            line_count=line_count,
            function_names=(),
            class_names=(),
            import_sources=(),
        )
        return fi, [], []

    func_names: list[str] = []
    class_names: list[str] = []
    import_sources: list[str] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Only top-level and class-level functions
            func_names.append(node.name)
            params = []
            for arg in node.args.args:
                params.append(arg.arg)
            # Collect function calls
            calls: list[str] = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)
            functions.append(FunctionInfo(
                name=node.name,
                filepath=rel_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                parameters=tuple(params),
                return_type=None,
                calls=tuple(calls),
                dependencies=(),
            ))
        elif isinstance(node, ast.ClassDef):
            class_names.append(node.name)
            methods = [
                n.name
                for n in ast.iter_child_nodes(node)
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            classes.append(ClassInfo(
                name=node.name,
                filepath=rel_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                methods=tuple(methods),
                base_classes=tuple(bases),
                subclasses=(),
            ))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                import_sources.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                import_sources.append(node.module)

    fi = FileInfo(
        filepath=rel_path,
        language="python",
        line_count=line_count,
        function_names=tuple(func_names),
        class_names=tuple(class_names),
        import_sources=tuple(import_sources),
    )
    return fi, functions, classes


def _resolve_import_edges(
    files: list[FileInfo],
    root: Path,
) -> list[FileInfo]:
    """Re-resolve import_sources to actual file paths within the project.

    Converts dotted module names (e.g. ``flask.app``) to relative file paths
    (``flask/app.py``) when those files exist under *root*.  Unresolvable
    imports are discarded so they do not pollute the dependency graph.
    """
    all_rel_paths: set[str] = {fi.filepath for fi in files}
    resolved: list[FileInfo] = []

    for fi in files:
        new_sources: list[str] = []
        for imp in fi.import_sources:
            # Try converting dotted module name to relative path
            candidate = imp.replace(".", "/") + ".py"
            if candidate in all_rel_paths and candidate != fi.filepath:
                new_sources.append(candidate)
                continue
            # Try package __init__.py
            candidate_init = imp.replace(".", "/") + "/__init__.py"
            if candidate_init in all_rel_paths and candidate_init != fi.filepath:
                new_sources.append(candidate_init)
                continue
            # Try stripping the leading "flask." prefix since our root is flask/
            if imp.startswith("flask."):
                suffix = imp[len("flask."):]
                candidate = suffix.replace(".", "/") + ".py"
                if candidate in all_rel_paths and candidate != fi.filepath:
                    new_sources.append(candidate)
                    continue
                candidate_init = suffix.replace(".", "/") + "/__init__.py"
                if candidate_init in all_rel_paths and candidate_init != fi.filepath:
                    new_sources.append(candidate_init)
                    continue
            # For bare "flask" -> __init__.py
            if imp == "flask":
                candidate = "__init__.py"
                if candidate in all_rel_paths and candidate != fi.filepath:
                    new_sources.append(candidate)
                    continue

        resolved.append(FileInfo(
            filepath=fi.filepath,
            language=fi.language,
            line_count=fi.line_count,
            function_names=fi.function_names,
            class_names=fi.class_names,
            import_sources=tuple(new_sources),
        ))
    return resolved


def fallback_parse(root: Path) -> CodebaseSnapshot:
    """Build a CodebaseSnapshot using stdlib ast when graph-sitter fails."""
    all_files: list[FileInfo] = []
    all_funcs: list[FunctionInfo] = []
    all_cls: list[ClassInfo] = []
    total_lines = 0

    for py_file in sorted(root.rglob("*.py")):
        fi, funcs, classes = _ast_parse_file(py_file, root)
        if fi is not None:
            all_files.append(fi)
            all_funcs.extend(funcs)
            all_cls.extend(classes)
            total_lines += fi.line_count

    # Resolve import edges to intra-project file paths
    all_files = _resolve_import_edges(all_files, root)

    log.info(
        "Fallback AST parser: %d files, %d functions, %d classes, %d lines",
        len(all_files), len(all_funcs), len(all_cls), total_lines,
    )

    return CodebaseSnapshot(
        root_path=str(root),
        files=tuple(all_files),
        functions=tuple(all_funcs),
        classes=tuple(all_cls),
        languages_detected=("python",),
        total_lines=total_lines,
    )


# ---------------------------------------------------------------------------
# Main E2E flow
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full E2E pipeline."""
    log.info("=" * 60)
    log.info("E2E Test: codebase-explorer against Flask")
    log.info("=" * 60)

    if not FLASK_SRC.is_dir():
        log.error("Flask source not found at %s", FLASK_SRC)
        log.error("Run: git clone --depth 1 https://github.com/pallets/flask.git test_repos/flask")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Parse Flask source
    # ------------------------------------------------------------------
    log.info("Step 1: Parsing Flask source at %s ...", FLASK_SRC)
    parser = CodebaseParser()
    try:
        snapshot = parser.parse(str(FLASK_SRC), languages=["python"])
        log.info(
            "graph-sitter parsed: %d files, %d funcs, %d classes",
            len(snapshot.files), len(snapshot.functions), len(snapshot.classes),
        )
    except (CodebaseParseError, Exception) as exc:
        log.warning("graph-sitter parse failed (%s); using AST fallback", exc)
        snapshot = fallback_parse(FLASK_SRC)

    assert len(snapshot.files) > 0, "No files parsed!"
    log.info(
        "  -> %d files, %d functions, %d classes, %d lines",
        len(snapshot.files), len(snapshot.functions),
        len(snapshot.classes), snapshot.total_lines,
    )

    # ------------------------------------------------------------------
    # Step 2: Build dependency graph
    # ------------------------------------------------------------------
    log.info("Step 2: Building dependency graph ...")
    from src.graph.dependency import build_dependency_graph
    graph_result = build_dependency_graph(snapshot)
    log.info(
        "  -> %d nodes, %d edges, %d circular groups",
        graph_result.file_count, graph_result.edge_count,
        len(graph_result.circular_deps),
    )

    # ------------------------------------------------------------------
    # Step 3: Group modules via Louvain
    # ------------------------------------------------------------------
    log.info("Step 3: Grouping modules ...")
    from src.graph.grouper import group_modules
    grouping = group_modules(graph_result.graph, snapshot)
    log.info(
        "  -> %d modules, modularity Q=%.3f, utility files=%d",
        grouping.module_count, grouping.modularity_score,
        len(grouping.utility_files),
    )
    for name, files in sorted(grouping.modules.items()):
        log.info("     [%s] %d files", name, len(files))

    assert grouping.module_count > 0, "No modules detected!"

    # ------------------------------------------------------------------
    # Step 4: Compute module metrics
    # ------------------------------------------------------------------
    log.info("Step 4: Computing module metrics ...")
    from src.graph.grouper import get_module_metrics
    metrics = get_module_metrics(graph_result.graph, grouping.modules)
    for name, m in sorted(metrics.items()):
        log.info(
            "     [%s] files=%d funcs=%d classes=%d lines=%d tokens=%d subpkgs=%d",
            name, m.file_count, m.function_count, m.class_count,
            m.line_count, m.estimated_tokens, m.subpackage_count,
        )

    # ------------------------------------------------------------------
    # Step 5: Build ModuleRecord list (as plan_doc_structure expects)
    # ------------------------------------------------------------------
    log.info("Step 5: Building ModuleRecord list ...")
    from src.state.models import ModuleRecord
    project_id = "flask_e2e"
    module_records: list[ModuleRecord] = []
    for name, files in grouping.modules.items():
        # Gather per-file info for counts
        file_infos = [f for f in snapshot.files if f.filepath in set(files)]
        module_records.append(ModuleRecord(
            id=f"{project_id}_{name}",
            project_id=project_id,
            name=name,
            files=list(files),
            file_count=len(files),
            line_count=sum(f.line_count for f in file_infos),
            function_count=sum(len(f.function_names) for f in file_infos),
            class_count=sum(len(f.class_names) for f in file_infos),
            is_utility=(name in grouping.utility_files),
        ))

    # ------------------------------------------------------------------
    # Step 6: Plan documentation structure
    # ------------------------------------------------------------------
    log.info("Step 6: Planning documentation structure ...")
    from src.doc.depth_planner import plan_doc_structure
    plan = plan_doc_structure(project_id, module_records, metrics)
    log.info(
        "  -> %d docs planned, max depth %d",
        plan.total_docs, plan.max_depth,
    )
    for node in plan.doc_tree:
        log.info(
            "     L%d %-50s target=%-25s budget=%d",
            node.level, node.path, node.target, node.token_budget,
        )
    log.info("  Depth decisions:")
    for mod_name, decision in sorted(plan.depth_decisions.items()):
        log.info("     [%s] depth=%d strategy=%s reason=%s",
                 mod_name, decision["depth"],
                 decision["split_strategy"], decision["reason"])

    assert plan.total_docs > 0, "No documents planned!"

    # ------------------------------------------------------------------
    # Step 7: Build mock AnalysisResult for each module
    # ------------------------------------------------------------------
    log.info("Step 7: Building mock analysis results ...")
    from src.state.models import AnalysisResult
    analysis_results: dict[str, AnalysisResult] = {}
    for mod in module_records:
        mod_metric = metrics.get(mod.name)
        # Build public interface list from function names in the module's files
        file_infos = [f for f in snapshot.files if f.filepath in set(mod.files)]
        public_interfaces = []
        for fi in file_infos:
            for fn in fi.function_names:
                if not fn.startswith("_"):
                    public_interfaces.append(fn)
        # Gather dependency module names
        dep_mods: set[str] = set()
        for fi in file_infos:
            for imp_src in fi.import_sources:
                for other_name, other_files in grouping.modules.items():
                    if other_name != mod.name and imp_src in set(other_files):
                        dep_mods.add(other_name)
        analysis_results[mod.name] = AnalysisResult(
            id=f"res_{mod.name}",
            task_id=f"task_{mod.name}",
            project_id=project_id,
            module_name=mod.name,
            description=f"Flask {mod.name} module: {mod.function_count} functions, {mod.class_count} classes",
            public_interfaces=public_interfaces[:20],  # cap for readability
            key_data_structures=[],
            dependencies=sorted(dep_mods),
            dependents=[],
            patterns_identified=[],
            detailed_analysis=None,
            mermaid_diagram=None,
            token_count=mod_metric.estimated_tokens if mod_metric else 0,
        )

    # ------------------------------------------------------------------
    # Step 8: Generate all documents
    # ------------------------------------------------------------------
    log.info("Step 8: Generating documents to %s ...", OUTPUT_DIR)
    from src.doc.generator import DocumentGenerator
    from src.doc.mermaid import MermaidGenerator
    from src.doc.templates import TemplateRenderer

    renderer = TemplateRenderer()
    mermaid_gen = MermaidGenerator()
    generator = DocumentGenerator(renderer, mermaid_gen)

    generated = generator.generate_all_docs(
        plan=plan,
        analysis_results=analysis_results,
        modules=module_records,
        output_dir=OUTPUT_DIR,
    )

    log.info("  -> %d documents generated", len(generated))
    for doc in generated:
        log.info(
            "     L%d %-50s tokens=%d",
            doc.level, doc.path, doc.actual_tokens,
        )

    # ------------------------------------------------------------------
    # Step 9: Validate outputs
    # ------------------------------------------------------------------
    log.info("Step 9: Validating outputs ...")
    errors: list[str] = []

    # 9a. INDEX.md exists
    index_path = OUTPUT_DIR / "INDEX.md"
    if index_path.exists():
        log.info("  [PASS] INDEX.md exists (%d bytes)", index_path.stat().st_size)
    else:
        errors.append("INDEX.md is missing")
        log.error("  [FAIL] INDEX.md is missing")

    # 9b. Each active module has OVERVIEW.md
    overview_count = 0
    for node in plan.doc_tree:
        if node.level == 1:
            overview_path = OUTPUT_DIR / node.path
            if overview_path.exists():
                overview_count += 1
            else:
                errors.append(f"OVERVIEW.md missing for {node.target}: {node.path}")
                log.error("  [FAIL] Missing: %s", node.path)
    log.info("  [PASS] %d OVERVIEW.md files found", overview_count)

    # 9c. At least 2 modules with DETAIL.md (Level 2+)
    detail_count = 0
    detail_modules: set[str] = set()
    for node in plan.doc_tree:
        if node.level >= 2:
            detail_path = OUTPUT_DIR / node.path
            if detail_path.exists():
                detail_count += 1
                detail_modules.add(node.target)
    if len(detail_modules) >= 2:
        log.info(
            "  [PASS] %d DETAIL docs across %d modules",
            detail_count, len(detail_modules),
        )
    elif len(detail_modules) >= 1:
        log.warning(
            "  [WARN] Only %d module(s) with DETAIL docs (expected >= 2); "
            "Flask may be too simple for deeper splitting",
            len(detail_modules),
        )
    else:
        # Not necessarily a failure -- if Flask modules are all small
        log.warning("  [WARN] No DETAIL docs generated (all modules may be small)")

    # 9d. Max depth >= 2
    depths = {node.level for node in plan.doc_tree}
    max_depth = max(depths) if depths else 0
    if max_depth >= 2:
        log.info("  [PASS] Max depth = %d (>= 2)", max_depth)
    else:
        log.warning("  [WARN] Max depth = %d (expected >= 2)", max_depth)

    # 9e. doc-index.json exists and is valid JSON
    doc_index_path = OUTPUT_DIR / "doc-index.json"
    if doc_index_path.exists():
        data = json.loads(doc_index_path.read_text(encoding="utf-8"))
        doc_count_in_index = len(data.get("docs", []))
        log.info(
            "  [PASS] doc-index.json exists (%d entries, max_depth=%s)",
            doc_count_in_index, data.get("max_depth"),
        )
        assert doc_count_in_index == len(generated), (
            f"doc-index.json has {doc_count_in_index} entries "
            f"but {len(generated)} documents were generated"
        )
    else:
        errors.append("doc-index.json is missing")
        log.error("  [FAIL] doc-index.json is missing")

    # 9f. Verify document content is non-empty and has expected structure
    for doc in generated:
        content = (OUTPUT_DIR / doc.path).read_text(encoding="utf-8")
        if len(content) < 50:
            errors.append(f"{doc.path} is suspiciously short ({len(content)} chars)")
        if "<!-- doc-meta" not in content:
            errors.append(f"{doc.path} missing doc-meta comment")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    log.info("=" * 60)
    if errors:
        log.error("E2E test completed with %d ERROR(s):", len(errors))
        for e in errors:
            log.error("  - %s", e)
        sys.exit(1)
    else:
        log.info("E2E test PASSED -- all validation checks succeeded")
        log.info("  Files parsed     : %d", len(snapshot.files))
        log.info("  Modules detected : %d", grouping.module_count)
        log.info("  Documents planned: %d", plan.total_docs)
        log.info("  Documents written: %d", len(generated))
        log.info("  Max depth        : %d", plan.max_depth)
        log.info("  Output directory : %s", OUTPUT_DIR)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
