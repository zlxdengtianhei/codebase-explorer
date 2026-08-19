"""Codebase Explorer MCP Server -- FastMCP entry point with 14 tools (V5).

V5 Architecture:
- No SQLite (replaced with JSON state file)
- No Jinja2 templates (docs written by LLM agents)
- 14 tools: analyze_codebase, get_structure, get_modules, get_function_deps,
  doc_operation, get_dependency_graph, get_progress, get_file_tokens, submit_analysis
  plus semantic progress, dependency-ready batch claim/submit, and blind review.
- Feature Cone based grouping (replaces Louvain as primary)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

import networkx as nx

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import build_task_manifest
from src.graph.feature_cone import extract_feature_cones, FeatureCone
from src.graph.strategies import get_strategy, list_strategies
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.ir import (
    EntityKind,
    Relation,
    SourceUnit,
    SourceUnitState,
    Symbol,
    deterministic_entity_id,
)
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.backend import PythonAstBackend, SyntaxArtifact
from src.parser.codebase import CodebaseParser, CodebaseParseError
from src.semantic.inventory import enumerate_python_files, enumerate_semantic_inventory
from src.semantic.service import (
    REVIEW_VERDICT_RELPATH,
    SemanticReviewError,
    SemanticService,
    SemanticServiceError,
    SemanticSubmissionError,
)
from src.server_helpers import (
    build_graph_from_dag,
    build_module_level_graph,
    compute_cone_layers,
    compute_inter_module_deps_from_dag,
    now_iso,
    project_id_from_path,
    render_mermaid,
    resolve_output_dir,
    resolve_project_dir,
    write_analysis_outputs,
)
from src.state.json_store import (
    JsonRunStore,
    RecoveryError,
    RunStoreError,
    read_state,
)
from src.state.migrate_v2_v3 import write_v2_rollback_projection
from src.state.models import LegacySubmissionSeed
from src.state.run_lifecycle import (
    ACTIVE_RECEIPT_NAME,
    ROUTE_KEYS,
    ActiveRunReceipt,
    LifecycleCacheMiss,
    LifecycleConflict,
    LifecycleError,
    active_receipt_hash,
    analysis_input_fingerprint,
    artifact_manifest,
    legacy_seed_sha256,
    promote_active_receipt,
    publish_generation,
    read_active_receipt,
    recover_interrupted_initial_activation,
    resolve_active_run,
    stage_v2_recovery_projection,
    V2_RECOVERY_PROJECTION_SHA_KEY,
)

logger = logging.getLogger(__name__)

MAX_HOPS = 5
"""Maximum number of hops for file-scope dependency graph traversal."""

# ---------------------------------------------------------------------------
# FastMCP Server Setup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Initialize parser for the server lifespan."""
    parser = CodebaseParser()
    yield {"parser": parser}


mcp = FastMCP(
    "codebase-explorer",
    instructions="Codebase analysis server with feature-cone grouping and token-aware task planning.",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Context Helpers
# ---------------------------------------------------------------------------


def _lc(ctx):
    """Get lifespan context."""
    return ctx.request_context.lifespan_context


def _parser(ctx) -> CodebaseParser:
    """Get parser from context."""
    return _lc(ctx)["parser"]


def _analysis_root_for_generation(project_dir: Path) -> Path:
    """Map ``.runs/<run>`` back to its analysis root without guessing a run."""

    if project_dir.parent.name == ".runs":
        return project_dir.parent.parent
    return project_dir


def _semantic_repo_root(output_dir: str | None = None) -> Path:
    """Resolve a canonical repository root without confusing it with a run."""

    if output_dir is not None:
        if not output_dir.strip():
            raise ToolError("Analysis directory must be a non-empty path or null")
        requested = Path(output_dir).expanduser()
        if not requested.exists():
            raise ToolError(f"Analysis directory does not exist: {requested}")
        if requested.is_symlink():
            raise ToolError("Semantic tools reject symlinked analysis paths")
    selected = resolve_project_dir(output_dir)
    analysis_root = _analysis_root_for_generation(selected).resolve()
    if analysis_root.is_symlink() or analysis_root.name != ".codebase-analysis":
        raise ToolError("Semantic tools require a canonical .codebase-analysis directory")

    receipt_path = analysis_root / ACTIVE_RECEIPT_NAME
    if receipt_path.is_file():
        try:
            active = resolve_active_run(analysis_root)
        except LifecycleError as exc:
            raise ToolError(f"Canonical analysis lifecycle is corrupt: {exc}") from exc
        if selected.parent.name == ".runs" and selected.resolve() != active.generation_path.resolve():
            raise ToolError("The requested generation is not the active canonical run")
        repo_root = Path(active.receipt.repo_root).resolve()
        if Path(active.snapshot.repo_root).resolve() != repo_root:
            raise ToolError("Active receipt and state disagree about repository root")
    else:
        state_path = analysis_root / "state.json"
        try:
            state = read_state(state_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ToolError(f"Cannot resolve semantic repository root: {exc}") from exc
        raw_root = state.get("path")
        if not isinstance(raw_root, str) or not raw_root:
            raise ToolError("Legacy analysis state does not identify its repository root")
        repo_root = Path(raw_root).resolve()

    if not repo_root.is_dir() or analysis_root != repo_root / ".codebase-analysis":
        raise ToolError("Analysis root and repository root fail the semantic identity check")
    return repo_root


def _python_semantic_ir(
    repo_root: Path,
) -> tuple[tuple[Symbol, ...], tuple[Relation, ...], tuple[object, ...]]:
    """Normalize probe-visible Python source into the C1/C2 IR bridge."""

    inventory = enumerate_semantic_inventory(repo_root)
    return _python_semantic_ir_cached(repo_root.as_posix(), inventory.source_revision)


@lru_cache(maxsize=8)
def _python_semantic_ir_cached(
    repo_root_text: str,
    source_revision: str,
) -> tuple[tuple[Symbol, ...], tuple[Relation, ...], tuple[object, ...]]:
    repo_root = Path(repo_root_text)
    ir_revision = "rev_" + hashlib.sha256(source_revision.encode("utf-8")).hexdigest()
    backend = PythonAstBackend(root=repo_root)
    adapter = PythonLanguageAdapter(repo_root)
    symbols = []
    relations = []
    call_site_inventories = []
    for path in enumerate_python_files(repo_root):
        relative = path.relative_to(repo_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        unit = SourceUnit(
            id=deterministic_entity_id(
                ir_revision,
                relative,
                EntityKind.SOURCE_UNIT,
                relative,
            ),
            source_revision_id=ir_revision,
            path=relative,
            language="python",
            content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            state=SourceUnitState.DISCOVERED,
            backend_id=backend.backend_id,
            backend_version=backend.backend_version,
        )
        artifact = backend.parse(unit)
        if not isinstance(artifact, SyntaxArtifact):
            continue
        normalized = adapter.normalize(artifact)
        if not isinstance(normalized, FileIR):
            continue
        symbols.extend(normalized.symbols)
        relations.extend(normalized.relations)
        if normalized.call_site_inventory is None:
            raise ValueError(
                f"Python normalization omitted CallSiteInventory for {relative}"
            )
        call_site_inventories.append(normalized.call_site_inventory)
    return tuple(symbols), tuple(relations), tuple(call_site_inventories)


def _semantic_module_map(repo_root: Path) -> dict[str, str]:
    """Project the canonical feature-cone partition onto unique file owners."""

    analysis_root = repo_root / ".codebase-analysis"
    if (analysis_root / ACTIVE_RECEIPT_NAME).is_file():
        try:
            cones_path = resolve_active_run(analysis_root).generation_path / "03_feature_cones.json"
        except LifecycleError as exc:
            raise ToolError(f"Cannot load canonical module partition: {exc}") from exc
    else:
        cones_path = analysis_root / "03_feature_cones.json"
    if not cones_path.is_file():
        return {}
    try:
        payload = json.loads(cones_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"Canonical module partition is corrupt: {exc}") from exc
    cones = payload.get("cones")
    infrastructure = payload.get("infrastructure_files", [])
    if not isinstance(cones, dict) or not isinstance(infrastructure, list):
        raise ToolError("Canonical module partition has an invalid shape")
    owners: dict[str, str] = {}
    for module_id, cone in sorted(cones.items()):
        files = cone.get("exclusive_files") if isinstance(cone, dict) else None
        if not isinstance(module_id, str) or not isinstance(files, list):
            raise ToolError("Canonical module partition has an invalid cone")
        for path in files:
            if not isinstance(path, str):
                raise ToolError("Canonical module partition contains a non-string path")
            prior = owners.get(path)
            if prior is not None and prior != module_id:
                raise ToolError(f"File has two exclusive semantic modules: {path}")
            owners[path] = module_id
    for path in infrastructure:
        if not isinstance(path, str):
            raise ToolError("Canonical infrastructure partition contains a non-string path")
        owners.setdefault(path, "shared_infrastructure")
    return owners


def _semantic_service(repo_root: Path) -> SemanticService:
    from src.graph.reverse_edges import build_reverse_index_from_ir

    symbols, relations, call_site_inventories = _python_semantic_ir(repo_root)
    reverse_index = build_reverse_index_from_ir(
        symbols,
        relations,
        call_site_inventories,
        repo=repo_root.name,
    )

    def renderer(
        render_root: str | Path,
        ledger,
        *,
        graph=None,
    ):
        from src.semantic.render import (
            discover_names_path,
            discover_partition_path,
            render_semantic_docs,
        )

        partition = discover_partition_path(repo_root)
        names = discover_names_path(repo_root, partition)
        return render_semantic_docs(
            render_root,
            ledger,
            graph=graph,
            reverse_index=reverse_index,
            partition_path=partition,
            names_path=names,
        )

    return SemanticService(
        repo_root,
        ir_symbols=symbols,
        relations=relations,
        module_by_file=_semantic_module_map(repo_root),
        renderer=renderer,
    )


def _semantic_summary(service: SemanticService, ledger) -> dict:
    return {
        "ledger_path": str(service.store.path),
        "docs_dir": str(service.repo_root / ".codebase-docs"),
        "source_revision": ledger.source_revision,
        "totals": ledger.totals.model_dump(mode="json"),
        "coverage_percent": ledger.coverage_percent,
    }


def _bootstrap_semantic(repo_root: Path) -> dict:
    try:
        service = _semantic_service(repo_root)
        ledger = service.bootstrap_semantic()
    except (SemanticServiceError, OSError, ValueError) as exc:
        raise ToolError(f"Semantic bootstrap failed: {exc}") from exc
    return _semantic_summary(service, ledger)


def _packet_payload(packet) -> dict | None:
    if packet is None:
        return None
    payload = asdict(packet)
    payload["lease_expires_at"] = packet.lease_expires_at.isoformat()
    return payload


HOST_SESSION_ENV_REGISTRY = (
    ("codex", "CODEX_THREAD_ID"),
    ("claude", "CLAUDE_CODE_SESSION_ID"),
    ("generic", "CBE_HOST_SESSION_ID"),
)


def _trusted_host_session_id() -> str:
    """Read host identity from server process state, never MCP input."""

    for host_kind, variable in HOST_SESSION_ENV_REGISTRY:
        value = os.environ.get(variable, "").strip()
        if value:
            return f"{host_kind}:{value}"
    accepted = ", ".join(variable for _, variable in HOST_SESSION_ENV_REGISTRY)
    raise ToolError(
        "Semantic production requires a trusted host session identity from "
        f"server process environment. Accepted variables, in priority order: {accepted}"
    )


def _ready_semantic_service(output_dir: str | None) -> SemanticService:
    repo_root = _semantic_repo_root(output_dir)
    service = _semantic_service(repo_root)
    if not service.store.path.is_file():
        raise ToolError("Semantic ledger not found. Run analyze_codebase first.")
    return service


def _render_paths(repo_root: Path) -> dict:
    docs_dir = repo_root / ".codebase-docs"
    return {
        "index_path": str(docs_dir / "INDEX.md"),
        "detail_paths": [str(path) for path in sorted(docs_dir.rglob("DETAIL.md"))],
    }


def _route_parent(snapshot, *, target: str, actor: str):
    matches = tuple(
        lease
        for lease in snapshot.leases
        if lease.target == target and lease.actor == actor
    )
    if len(matches) != 1:
        raise ToolError(f"Canonical route parent is unavailable for {actor}")
    return matches[0]


# ---------------------------------------------------------------------------
# Tool 1: analyze_codebase
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True})
async def analyze_codebase(
    path: Annotated[str, Field(description="Absolute path to the codebase root")],
    languages: Annotated[
        list[Literal["python", "typescript", "javascript"]] | None,
        Field(description="Languages to analyze. None = auto-detect."),
    ] = None,
    output_dir: Annotated[
        str | None,
        Field(description="Output directory for JSON files. None = {path}/.codebase-analysis/"),
    ] = None,
    force_reindex: Annotated[
        bool, Field(description="Force reindex even if cache exists.")
    ] = False,
    exclude_paths: Annotated[
        list[str] | None,
        Field(description="Additional directory/file paths to exclude from analysis (e.g. ['vendor/', 'generated/'])"),
    ] = None,
    include_tests: Annotated[
        bool, Field(description="Include test directories (tests/, test/) in analysis. Default: False."),
    ] = False,
    ctx: Context = None,
) -> dict:
    """Run complete analysis pipeline and generate 5 JSON files + state.json.

    This is the main entry point that replaces V1's index_codebase + create_analysis_plan.
    Performs purely deterministic analysis (no LLM calls).

    Pipeline:
      1. Parse codebase → CodebaseSnapshot
      2. Build weighted dependency graph → nx.DiGraph
      3. Extract feature cones via SCC + DAG analysis
      4. Estimate tokens per file (chars ÷ 4)
      5. Build task manifest (greedy bin packing)
      6. Write 5 JSON files + state.json

    Returns:
        Project metadata and paths to all generated files.
    """
    resolved_path = Path(path).resolve()
    if not resolved_path.is_dir():
        raise ToolError(f"Not a directory: {path}")

    output_path = resolve_output_dir(str(resolved_path), output_dir)
    project_id = project_id_from_path(str(resolved_path))
    requested_languages = tuple(languages or ())
    input_fingerprint = analysis_input_fingerprint(
        languages=requested_languages,
        exclude_paths=tuple(exclude_paths or ()),
        include_tests=include_tests,
    )

    prior_receipt = None
    if (output_path / ACTIVE_RECEIPT_NAME).exists():
        try:
            active = resolve_active_run(
                output_path,
                expected_repo_root=resolved_path,
                expected_input_fingerprint=input_fingerprint,
                require_fresh_source=True,
                require_unexpired_routes=True,
            )
        except LifecycleCacheMiss:
            active = None
        except LifecycleError as exc:
            raise ToolError(f"Canonical analysis lifecycle is corrupt: {exc}") from exc
        prior_receipt = read_active_receipt(output_path)
        if active is not None and not force_reindex:
            generation = active.generation_path
            logger.info("[analyze_codebase] Canonical cache hit for %s", resolved_path)
            semantic = _bootstrap_semantic(resolved_path)
            return {
                "status": "success",
                "project_id": project_id,
                "output_dir": str(output_path),
                "cached": True,
                "message": "Using cached analysis results",
                "files": {
                    "01_structure": str(generation / "01_structure.json"),
                    "02_dag": str(generation / "02_dag.json"),
                    "03_feature_cones": str(generation / "03_feature_cones.json"),
                    "04_file_tokens": str(generation / "04_file_tokens.json"),
                    "05_task_manifest": str(generation / "05_task_manifest.json"),
                },
                "state_file": str(output_path / "state.json"),
                "canonical_state_file": str(active.state_path),
                "run_id": active.receipt.run_id,
                "active_run_receipt": str(output_path / ACTIVE_RECEIPT_NAME),
                "semantic": semantic,
            }
    else:
        generations = output_path / ".runs"
        if generations.exists() and any(generations.iterdir()):
            try:
                active = recover_interrupted_initial_activation(
                    output_path,
                    expected_repo_root=resolved_path,
                    expected_input_fingerprint=input_fingerprint,
                )
            except LifecycleError as exc:
                raise ToolError(
                    f"Canonical generations exist without a recoverable active receipt: {exc}"
                ) from exc
            prior_receipt = active.receipt
            if not force_reindex:
                generation = active.generation_path
                semantic = _bootstrap_semantic(resolved_path)
                return {
                    "status": "success",
                    "project_id": project_id,
                    "output_dir": str(output_path),
                    "cached": True,
                    "message": "Using recovered cached analysis results",
                    "files": {
                        "01_structure": str(generation / "01_structure.json"),
                        "02_dag": str(generation / "02_dag.json"),
                        "03_feature_cones": str(generation / "03_feature_cones.json"),
                        "04_file_tokens": str(generation / "04_file_tokens.json"),
                        "05_task_manifest": str(generation / "05_task_manifest.json"),
                    },
                    "state_file": str(output_path / "state.json"),
                    "canonical_state_file": str(active.state_path),
                    "run_id": active.receipt.run_id,
                    "active_run_receipt": str(output_path / ACTIVE_RECEIPT_NAME),
                    "semantic": semantic,
                }
        legacy_v2 = output_path / "state.json"
        legacy_artifacts = tuple(output_path / name for name in (
            "01_structure.json", "02_dag.json", "03_feature_cones.json",
            "04_file_tokens.json", "05_task_manifest.json", "06_function_deps.json",
        ))
        if legacy_v2.exists():
            try:
                legacy = json.loads(legacy_v2.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ToolError(f"Legacy V2 state is corrupt: {exc}") from exc
            if legacy.get("project_id") != project_id or Path(
                legacy.get("path", "")
            ).resolve() != resolved_path:
                raise ToolError("Legacy V2 state does not match the requested project/root")
            if not all(path.is_file() for path in legacy_artifacts):
                raise ToolError("Legacy V2 output is incomplete and cannot be upgraded safely")
        elif any(path.exists() for path in legacy_artifacts):
            raise ToolError("Legacy artifacts exist without a V2 lineage anchor")

    # Ensure output directory exists.  All new bytes remain unselected until
    # the same-directory generation publish and selector CAS complete.
    output_path.mkdir(parents=True, exist_ok=True)
    run_id = f"run-{uuid.uuid4().hex}"
    staging_path = output_path / ".staging" / run_id
    staging_path.mkdir(parents=True, exist_ok=False)

    # Step 1: Parse codebase
    logger.info(f"[analyze_codebase] Parsing {resolved_path}...")
    try:
        snapshot = _parser(ctx).parse(str(resolved_path), languages=languages)
    except CodebaseParseError as e:
        raise ToolError(str(e)) from e

    # Step 1b: Filter files based on exclude_paths and include_tests
    _test_dirs = {"tests/", "test/", "tests\\", "test\\"}
    user_excludes = set(exclude_paths or [])

    def _should_exclude(filepath: str) -> bool:
        # User-specified exclusions
        for excl in user_excludes:
            if filepath.startswith(excl) or ("/" + excl) in filepath:
                return True
        # Test directory exclusion (unless include_tests is True)
        if not include_tests:
            for td in _test_dirs:
                if filepath.startswith(td) or ("/" + td) in filepath:
                    return True
        return False

    filtered_files = tuple(f for f in snapshot.files if not _should_exclude(f.filepath))
    filtered_funcs = tuple(f for f in snapshot.functions if not _should_exclude(f.filepath))
    filtered_classes = tuple(c for c in snapshot.classes if not _should_exclude(c.filepath))

    if len(filtered_files) < len(snapshot.files):
        from src.parser.codebase import CodebaseSnapshot
        excluded_count = len(snapshot.files) - len(filtered_files)
        logger.info("[analyze_codebase] Excluded %d files (exclude_paths=%s, include_tests=%s)",
                     excluded_count, exclude_paths, include_tests)
        snapshot = CodebaseSnapshot(
            root_path=snapshot.root_path,
            files=filtered_files,
            functions=filtered_funcs,
            classes=filtered_classes,
            languages_detected=snapshot.languages_detected,
            total_lines=sum(f.line_count for f in filtered_files),
        )

    # Step 2: Build weighted dependency graph
    logger.info("[analyze_codebase] Building weighted dependency graph...")
    weighted_result = build_weighted_dependency_graph(snapshot)
    graph = weighted_result.graph

    # Step 3: Extract feature cones via pluggable strategy
    logger.info("[analyze_codebase] Extracting feature cones...")
    strategy = get_strategy()
    strategy_result = strategy.group(graph, snapshot)
    # Convert StrategyResult back to (cones, infrastructure) for downstream pipeline
    entry_points = strategy_result.metadata.get("entry_points", {})
    cones: dict[str, FeatureCone] = {}
    for mid, mod in strategy_result.modules.items():
        cones[mid] = FeatureCone(
            cone_id=mod.module_id,
            entry_point=entry_points.get(mid, mod.files[0] if mod.files else mid),
            exclusive_files=mod.files,
            shared_deps=mod.depends_on,
            layer=mod.layer,
            token_count=mod.token_count,
        )
    infrastructure = frozenset(strategy_result.infrastructure)
    logger.info(
        f"[analyze_codebase] Found {len(cones)} cones, {len(infrastructure)} infrastructure files "
        f"(strategy={strategy_result.strategy_used})"
    )

    # Step 3b: DAG layer calculation via SCC condensation + topological ordering
    # First: compute file-level layers using SCC condensation on the full graph
    condensed = nx.condensation(graph)
    file_layer: dict[str, int] = {}
    # Kahn-style layer assignment on condensed DAG
    remaining = set(condensed.nodes())
    layer_idx = 0
    while remaining:
        current = {n for n in remaining if all(p not in remaining for p in condensed.predecessors(n))}
        if not current:
            current = remaining.copy()
        for scc_node in current:
            members = condensed.nodes[scc_node].get("members", set())
            for member in members:
                file_layer[member] = layer_idx
        remaining -= current
        layer_idx += 1
    total_layers = layer_idx

    # Derive cone layer = max file layer among exclusive files
    cone_layer: dict[str, int] = {}
    for cid, cone in cones.items():
        if cone.exclusive_files:
            cone_layer[cid] = max(file_layer.get(f, 0) for f in cone.exclusive_files)
        else:
            cone_layer[cid] = 0

    logger.info("[PIPELINE] SCC condensation: %d components, DAG layering: %d layers computed",
                condensed.number_of_nodes(), total_layers)

    updated_cones: dict[str, FeatureCone] = {}
    for cid, cone in cones.items():
        updated_cones[cid] = FeatureCone(
            cone_id=cone.cone_id, entry_point=cone.entry_point,
            exclusive_files=cone.exclusive_files, shared_deps=cone.shared_deps,
            layer=cone_layer.get(cid, 0), token_count=cone.token_count,
        )
    cones = updated_cones

    # Step 3c: Louvain fallback when feature cones are degraded
    single_file = sum(1 for c in cones.values() if len(c.exclusive_files) <= 1)
    if len(cones) > 3 and single_file / len(cones) > 0.7:
        logger.warning(
            "[PIPELINE] Louvain fallback triggered — feature cones degraded (%d/%d single-file)",
            single_file, len(cones),
        )
        from src.graph.grouper import group_modules
        grouping = group_modules(graph, snapshot)
        cones = {}
        for mod_name, mod_files in grouping.modules.items():
            cones[mod_name] = FeatureCone(
                cone_id=mod_name, entry_point=mod_name,
                exclusive_files=tuple(mod_files), shared_deps=(),
            )
        infrastructure = grouping.utility_files
        logger.info("[PIPELINE] Louvain produced %d modules", len(cones))

    logger.info(
        "[PIPELINE] feature cones: %d cones, %d layers",
        len(cones), total_layers,
    )

    # Step 4: Estimate tokens per file
    logger.info("[analyze_codebase] Estimating tokens...")
    file_tokens = {}
    file_details = []
    for file_info in snapshot.files:
        lang = file_info.language or "default"
        tokens = estimate_tokens_from_chars(file_info.char_count, lang)
        file_tokens[file_info.filepath] = tokens
        file_details.append(
            {
                "filepath": file_info.filepath,
                "language": lang,
                "char_count": file_info.char_count,
                "line_count": file_info.line_count,
                "estimated_tokens": tokens,
                "method": "chars",
            }
        )

    # Step 5: Build DAG layers and task manifest
    logger.info("[analyze_codebase] Building task manifest...")

    # Pre-build dag_edges list for cone layer computation and cohesion scoring
    dag_edges_list = [
        {
            "source": u,
            "target": v,
            "weight": graph[u][v].get("weight", 1),
            "edge_types": graph[u][v].get("edge_types", []),
        }
        for u, v in graph.edges()
    ]
    dag_nodes_list = list(graph.nodes())

    cone_dicts = {}
    for cone_id, cone in cones.items():
        cone_tokens = sum(file_tokens.get(f, 0) for f in cone.exclusive_files)
        exclusive_set = set(cone.exclusive_files)

        # Compute layers within this cone
        layers_within = compute_cone_layers(
            list(cone.exclusive_files), dag_nodes_list, dag_edges_list,
        )

        # Compute cohesion score: internal_edges / max(total_edges, 1)
        internal_edges = 0
        total_edges = 0
        for u, v in graph.edges():
            u_in = u in exclusive_set
            v_in = v in exclusive_set
            if u_in or v_in:
                total_edges += 1
                if u_in and v_in:
                    internal_edges += 1
        cohesion = internal_edges / max(total_edges, 1)

        cone_dicts[cone_id] = {
            "cone_id": cone_id,
            "entry_point": cone.entry_point,
            "exclusive_files": cone.exclusive_files,
            "shared_deps": cone.shared_deps,
            "layer": cone.layer,
            "token_count": cone_tokens,
            "layers_within_cone": layers_within,
            "cohesion_score": round(cohesion, 4),
        }

    task_manifest = build_task_manifest(cone_dicts, file_tokens)

    # Step 6: Write JSON files + state.json
    v2_projection = write_analysis_outputs(
        output_path=staging_path,
        project_id=project_id,
        resolved_path=resolved_path,
        snapshot=snapshot,
        weighted_result=weighted_result,
        graph=graph,
        cones=cones,
        infrastructure=infrastructure,
        cone_dicts=cone_dicts,
        file_tokens=file_tokens,
        file_details=file_details,
        task_manifest=task_manifest,
    )
    # The helper writes into a transient generation staging directory, while
    # the immutable rollback projection must retain the stable analysis root.
    v2_projection["documentation"]["output_dir"] = str(output_path)
    v2_recovery_projection_sha = stage_v2_recovery_projection(
        staging_path, v2_projection
    )

    seed = LegacySubmissionSeed(
        task_ids=tuple(task_manifest.get("tasks", {}).keys()),
        source_file_count=len(snapshot.files),
    )
    store = JsonRunStore(staging_path / "state-v3.json")
    begin_actor = "orchestrator/legacy-mcp/analyze_codebase"
    now = datetime.now(UTC)
    bootstrap = store.issue_bootstrap_lease(
        run_id=run_id,
        actor=begin_actor,
        ttl=timedelta(days=1),
        now=now,
    )
    begin = store.begin_run(
        run_id=run_id,
        repo_root=resolved_path,
        requested_languages=tuple(languages or snapshot.languages_detected),
        actor=begin_actor,
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        exclude_globs=tuple(exclude_paths or ()),
        product_output_roots=(output_path,),
        route_keys=ROUTE_KEYS,
        legacy_submission_seed=seed,
        initial_metadata={
            "project_id": project_id,
            "analysis_root": str(output_path),
            "analysis_input_fingerprint": input_fingerprint,
            V2_RECOVERY_PROJECTION_SHA_KEY: v2_recovery_projection_sha,
        },
        now=now,
    )
    # Reopen before publish so an incomplete V3 never reaches the selector.
    JsonRunStore(staging_path / "state-v3.json").snapshot()
    generation = publish_generation(output_path, staging_path, run_id)
    snapshot_v3 = JsonRunStore(generation / "state-v3.json").snapshot()

    v2_path = output_path / "state.json"
    if not v2_path.exists():
        write_v2_rollback_projection(v2_path, v2_projection, snapshot=snapshot_v3)
    v2_hash = hashlib.sha256(v2_path.read_bytes()).hexdigest()
    prior_hash = active_receipt_hash(output_path)
    prior_generation = prior_receipt.activation_generation if prior_receipt else 0
    receipt = ActiveRunReceipt(
        activation_generation=prior_generation + 1,
        run_id=run_id,
        generation_path=f".runs/{run_id}",
        state_path=f".runs/{run_id}/state-v3.json",
        repo_root=str(resolved_path),
        analysis_input_fingerprint=input_fingerprint,
        source_revision=snapshot_v3.revisions.source,
        v2_sha256=v2_hash,
        artifacts=artifact_manifest(generation),
        legacy_seed_sha256=legacy_seed_sha256(seed),
        route_keys=ROUTE_KEYS,
        prior_receipt_sha256=prior_hash,
    )
    try:
        promote_active_receipt(
            output_path,
            receipt,
            expected_prior_hash=prior_hash,
            expected_generation=prior_generation,
        )
    except LifecycleConflict as exc:
        raise ToolError(f"Canonical activation conflict: {exc}") from exc

    logger.info(f"[analyze_codebase] Analysis complete. Output: {output_path}")
    semantic = _bootstrap_semantic(resolved_path)

    return {
        "status": "success",
        "project_id": project_id,
        "output_dir": str(output_path),
        "cached": False,
        "files_analyzed": len(snapshot.files),
        "feature_cones_found": len(cones),
        "task_count": len(task_manifest.get("tasks", {})),
        "total_tokens": sum(file_tokens.values()),
        "files": {
            "01_structure": str(generation / "01_structure.json"),
            "02_dag": str(generation / "02_dag.json"),
            "03_feature_cones": str(generation / "03_feature_cones.json"),
            "04_file_tokens": str(generation / "04_file_tokens.json"),
            "05_task_manifest": str(generation / "05_task_manifest.json"),
        },
        "state_file": str(output_path / "state.json"),
        "canonical_state_file": str(generation / "state-v3.json"),
        "run_id": run_id,
        "active_run_receipt": str(output_path / ACTIVE_RECEIPT_NAME),
        "semantic": semantic,
    }


# ---------------------------------------------------------------------------
# Tools 1b-1f: semantic lifecycle and independent review
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False})
async def get_semantic_progress(
    output_dir: Annotated[
        str | None,
        Field(description="Path to the canonical .codebase-analysis directory."),
    ] = None,
) -> dict:
    """Recompute semantic coverage from source truth and the canonical ledger."""

    service = _ready_semantic_service(output_dir)
    try:
        progress = service.get_semantic_progress()
    except (SemanticServiceError, OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"Cannot read semantic progress: {exc}") from exc
    return {
        "status": "success",
        "output_dir": str(service.repo_root / ".codebase-analysis"),
        "ledger_path": str(service.store.path),
        "docs_dir": str(service.repo_root / ".codebase-docs"),
        **progress,
    }


@mcp.tool(annotations={"readOnlyHint": False})
async def claim_semantic_batch(
    max_context_tokens: Annotated[
        int,
        Field(description="Host context window used for deterministic packet budgeting."),
    ],
    lease_seconds: Annotated[
        int,
        Field(description="Exclusive lease lifetime in seconds."),
    ] = 900,
    output_dir: Annotated[
        str | None,
        Field(description="Path to the canonical .codebase-analysis directory."),
    ] = None,
) -> dict:
    """Claim one dependency-ready, replayable semantic source packet."""

    service = _ready_semantic_service(output_dir)
    try:
        packet = service.claim_semantic_batch(
            actor=_trusted_host_session_id(),
            max_context_tokens=max_context_tokens,
            lease_seconds=lease_seconds,
        )
    except (SemanticServiceError, OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"Cannot claim semantic batch: {exc}") from exc
    return {
        "status": "success",
        "packet": _packet_payload(packet),
        "done": packet is None,
    }


@mcp.tool(annotations={"readOnlyHint": False})
async def submit_semantic_batch(
    batch_id: Annotated[str, Field(description="Claimed semantic batch identity.")],
    source_revision: Annotated[
        str,
        Field(description="Exact source revision copied from the claimed packet."),
    ],
    explanations: Annotated[
        list[dict],
        Field(description="Full batch explanations as {symbol_id, text} objects."),
    ],
    residuals: Annotated[
        list[dict] | None,
        Field(description="Optional terminal residuals as {symbol_id, reason} objects."),
    ] = None,
    output_dir: Annotated[
        str | None,
        Field(description="Path to the canonical .codebase-analysis directory."),
    ] = None,
) -> dict:
    """Atomically accept one full batch into ledger and readable documents."""

    explanation_map: dict[str, str] = {}
    for item in explanations:
        if not isinstance(item, dict) or set(item) != {"symbol_id", "text"}:
            raise ToolError("Each explanation must contain only symbol_id and text")
        symbol_id = item["symbol_id"]
        text = item["text"]
        if not isinstance(symbol_id, str) or not isinstance(text, str):
            raise ToolError("Explanation symbol_id and text must be strings")
        if symbol_id in explanation_map:
            raise ToolError(f"Duplicate explanation symbol_id: {symbol_id}")
        explanation_map[symbol_id] = text

    residual_map: dict[str, str] = {}
    for item in residuals or []:
        if not isinstance(item, dict) or set(item) != {"symbol_id", "reason"}:
            raise ToolError("Each residual must contain only symbol_id and reason")
        symbol_id = item["symbol_id"]
        reason = item["reason"]
        if not isinstance(symbol_id, str) or not isinstance(reason, str):
            raise ToolError("Residual symbol_id and reason must be strings")
        if symbol_id in residual_map:
            raise ToolError(f"Duplicate residual symbol_id: {symbol_id}")
        residual_map[symbol_id] = reason

    service = _ready_semantic_service(output_dir)
    try:
        ledger = service.submit_semantic_batch(
            batch_id=batch_id,
            actor=_trusted_host_session_id(),
            source_revision=source_revision,
            explanations=explanation_map,
            residuals=residual_map,
        )
        accepted = service.get_semantic_submission_result(batch_id)
        progress = service.get_semantic_progress()
    except (SemanticSubmissionError, SemanticServiceError, OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"Semantic batch rejected: {exc}") from exc
    return {
        "status": "success",
        "accepted_symbol_ids": accepted["explanation_symbol_ids"],
        "residual_symbol_ids": accepted["residual_symbol_ids"],
        "ledger_path": str(service.store.path),
        "render": _render_paths(service.repo_root),
        "progress": progress,
        "source_revision": ledger.source_revision,
        "batch_released": True,
    }


@mcp.tool(annotations={"readOnlyHint": False})
async def get_semantic_review_batch(
    output_dir: Annotated[
        str | None,
        Field(description="Path to the canonical .codebase-analysis directory."),
    ] = None,
) -> dict:
    """Create a deterministic blind sample without exposing producer metadata."""

    service = _ready_semantic_service(output_dir)
    try:
        packet = service.get_semantic_review_batch()
    except (SemanticReviewError, SemanticServiceError, OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"Cannot create semantic review batch: {exc}") from exc
    return {"status": "success", **packet}


@mcp.tool(annotations={"readOnlyHint": False})
async def submit_semantic_review(
    review_batch_id: Annotated[
        str,
        Field(
            description=(
                "Opaque batch receipt returned by get_semantic_review_batch; "
                "the server owns independent reviewer dispatch and identity."
            )
        ),
    ],
    output_dir: Annotated[
        str | None,
        Field(description="Path to the canonical .codebase-analysis directory."),
    ] = None,
) -> dict:
    """Dispatch an isolated Codex reviewer and atomically consume its verdict."""

    service = _ready_semantic_service(output_dir)
    try:
        result = service.submit_semantic_review(
            review_batch_id=review_batch_id,
        )
        progress = service.get_semantic_progress()
    except (SemanticReviewError, SemanticServiceError, OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"Semantic review rejected: {exc}") from exc
    revisions = list(result["revision_symbol_ids"])
    return {
        "status": "revision_required" if revisions else "accepted",
        "reviewer_session_id": result["reviewer_session_id"],
        "artifact_path": result["verdict_path"],
        "revision_symbol_ids": revisions,
        "progress": progress,
    }


# ---------------------------------------------------------------------------
# Tool 2: get_structure
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_structure(
    module: Annotated[str | None, Field(description="Module/cone name")] = None,
    file: Annotated[str | None, Field(description="File path")] = None,
    function: Annotated[str | None, Field(description="Function name")] = None,
    detail: Annotated[bool, Field(description="Include per-file function_names, class_names, import_sources")] = False,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Query code structure from 01_structure.json.

    Three mutually exclusive query modes:
    - module: Get all files in a cone/module
    - file: Get detailed info for a single file
    - function: Get function signature and dependencies
    - None: Return project summary
    """
    project_dir = resolve_project_dir(output_dir)

    structure_path = project_dir / "01_structure.json"
    if not structure_path.exists():
        raise ToolError(f"Structure file not found: {structure_path}")

    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    files = structure.get("files", [])

    # Mode: Summary
    if not any([module, file, function]):
        language_breakdown = {}
        for f in files:
            lang = f.get("language", "unknown")
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1

        # Find most imported files
        import_counts = {}
        for f in files:
            for imp in f.get("import_sources", []):
                import_counts[imp] = import_counts.get(imp, 0) + 1
        most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "status": "success",
            "query_type": "summary",
            "file_count": structure.get("file_count", 0),
            "function_count": structure.get("function_count", 0),
            "class_count": structure.get("class_count", 0),
            "language_breakdown": language_breakdown,
            "most_imported_files": [
                {"filepath": fp, "import_count": cnt} for fp, cnt in most_imported
            ],
        }

    # Mode: Module/Cone query
    if module:
        # Load feature cones to get files in the module
        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError("Feature cones file not found")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(module)
        if not cone:
            raise ToolError(f"Module/cone '{module}' not found")

        module_files = [
            f for f in files if f["filepath"] in cone.get("exclusive_files", [])
        ]

        # When detail=False, strip verbose per-file fields for slim response
        if not detail:
            module_files = [
                {k: v for k, v in f.items() if k not in ("function_names", "class_names", "import_sources")}
                for f in module_files
            ]

        return {
            "status": "success",
            "query_type": "module",
            "module_name": module,
            "files": module_files,
            "file_count": len(module_files),
            "total_functions": sum(len(f.get("function_names", [])) for f in files if f["filepath"] in cone.get("exclusive_files", [])),
            "total_classes": sum(len(f.get("class_names", [])) for f in files if f["filepath"] in cone.get("exclusive_files", [])),
        }

    # Mode: File query
    if file:
        file_info = next((f for f in files if f["filepath"] == file), None)
        if not file_info:
            raise ToolError(f"File not found: {file}")

        # Build reverse index (imported_by)
        imported_by = []
        for f in files:
            if file in f.get("import_sources", []):
                imported_by.append(f["filepath"])

        return {
            "status": "success",
            "query_type": "file",
            "filepath": file_info["filepath"],
            "language": file_info.get("language", "unknown"),
            "line_count": file_info.get("line_count", 0),
            "functions": [
                {
                    "name": fn,
                    # Note: function details not available in structure.json
                    # Would need to parse functions array from snapshot
                }
                for fn in file_info.get("function_names", [])
            ],
            "classes": [
                {"name": cn} for cn in file_info.get("class_names", [])
            ],
            "import_sources": file_info.get("import_sources", []),
            "imported_by": imported_by,
        }

    # Mode: Function query
    if function:
        matches = []
        for f in files:
            if function in f.get("function_names", []):
                matches.append(
                    {
                        "filepath": f["filepath"],
                        # Note: line_start, line_end, calls not available in structure.json
                    }
                )

        if not matches:
            raise ToolError(f"Function '{function}' not found")

        return {
            "status": "success",
            "query_type": "function",
            "function_name": function,
            "matches": matches,
        }

    # Should not reach here
    raise ToolError("Invalid query parameters")


# ---------------------------------------------------------------------------
# Tool 3: get_modules (V5 format)
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_modules(
    module_id: Annotated[
        str | None,
        Field(description="Module ID for detail view. None = summary of all modules."),
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Query functional modules in V5 format.

    Two modes:
    - Summary (no args): Module list with metadata only (<3KB). No file lists.
    - Detail (module_id): Single module with file list and token counts.

    Use summary first to get module IDs, then detail for specific modules.
    """
    project_dir = resolve_project_dir(output_dir)

    cones_path = project_dir / "03_feature_cones.json"
    if not cones_path.exists():
        raise ToolError("Feature cones not found. Run analyze_codebase first.")

    cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
    cones = cones_data.get("cones", {})
    infra_files = cones_data.get("infrastructure_files", [])

    # Load file tokens
    tokens_path = project_dir / "04_file_tokens.json"
    file_tokens: dict[str, int] = {}
    if tokens_path.exists():
        tokens_data = json.loads(tokens_path.read_text(encoding="utf-8"))
        for ft in tokens_data.get("files", []):
            file_tokens[ft["filepath"]] = ft.get("estimated_tokens", 0)

    def _dir_hint(files: tuple | list) -> str:
        if not files:
            return ""
        dirs: dict[str, int] = {}
        for f in files:
            d = str(Path(f).parent)
            dirs[d] = dirs.get(d, 0) + 1
        return max(dirs.items(), key=lambda x: x[1])[0] + "/"

    def _friendly_name(cone_id: str) -> str:
        return cone_id.replace("_", " ").replace("::", " / ").title()

    # --- Summary mode (no module_id) ---
    if not module_id:
        total_files = sum(len(c.get("exclusive_files", [])) for c in cones.values())
        total_tokens = sum(c.get("token_count", 0) for c in cones.values())
        infra_tokens = sum(file_tokens.get(f, 0) for f in infra_files)

        # Compute inter-module deps from DAG edges (not just shared_deps)
        dag_path = project_dir / "02_dag.json"
        dag_edges: list[dict] = []
        if dag_path.exists():
            dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
            dag_edges = dag_data.get("edges", [])

        inter_module_deps = compute_inter_module_deps_from_dag(
            cones, dag_edges, infrastructure_files=infra_files,
        )

        modules = []
        total_dep_edges = 0
        modules_with_deps = 0
        for cid, cone in cones.items():
            dep_set = inter_module_deps.get(cid, set())
            total_dep_edges += len(dep_set)
            if dep_set:
                modules_with_deps += 1
            modules.append({
                "module_id": cid,
                "name": _friendly_name(cid),
                "file_count": len(cone.get("exclusive_files", [])),
                "token_count": cone.get("token_count", 0),
                "layer": cone.get("layer", 0),
                "depends_on": sorted(dep_set),
                "directory_hint": _dir_hint(cone.get("exclusive_files", [])),
            })

        return {
            "status": "success",
            "total_modules": len(cones),
            "total_files": total_files,
            "total_tokens": total_tokens,
            "grouping": {
                "strategy_used": "feature_cone",
            },
            "token_budget": {
                "budget_limit": 100_000,
            },
            "inter_module_deps": {
                "total_edges": total_dep_edges,
                "modules_with_deps": modules_with_deps,
            },
            "modules": modules,
            "infrastructure": {
                "file_count": len(infra_files),
                "token_count": infra_tokens,
                "files": infra_files,
            },
        }

    # --- Detail mode (specific module_id) ---

    # Handle infrastructure pseudo-module
    if module_id == "infrastructure":
        infra_tokens = sum(file_tokens.get(f, 0) for f in infra_files)
        infra_with_tokens = [
            {"filepath": f, "token_count": file_tokens.get(f, 0)}
            for f in infra_files
        ]
        return {
            "status": "success",
            "module_id": "infrastructure",
            "name": "Infrastructure & Shared Utilities",
            "layer": 0,
            "depends_on": [],
            "files": infra_with_tokens,
            "internal_layers": [],
            "token_count": infra_tokens,
        }

    cone = cones.get(module_id)
    if not cone:
        raise ToolError(f"Module '{module_id}' not found")

    exclusive_files = cone.get("exclusive_files", [])
    files_with_tokens = [
        {"filepath": f, "token_count": file_tokens.get(f, 0)}
        for f in exclusive_files
    ]

    # Compute inter-module deps from DAG edges (consistent with summary mode)
    dag_path = project_dir / "02_dag.json"
    dag_edges: list[dict] = []
    internal_layers: list[list[str]] = []
    if dag_path.exists():
        dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
        dag_edges = dag_data.get("edges", [])
        cone_files = list(exclusive_files) + list(cone.get("shared_deps", []))
        internal_layers = compute_cone_layers(
            cone_files, dag_data.get("nodes", []), dag_edges,
        )

    inter_module_deps = compute_inter_module_deps_from_dag(
        cones, dag_edges, infrastructure_files=infra_files,
    )
    deps = sorted(inter_module_deps.get(module_id, set()))

    return {
        "status": "success",
        "module_id": module_id,
        "name": _friendly_name(module_id),
        "layer": cone.get("layer", 0),
        "depends_on": deps,
        "files": files_with_tokens,
        "internal_layers": internal_layers,
        "token_count": cone.get("token_count", 0),
    }


# ---------------------------------------------------------------------------
# Tool 3c: get_function_deps
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_function_deps(
    file: Annotated[str, Field(description="File path to query function dependencies for")],
    module_id: Annotated[
        str | None,
        Field(description="Optional: limit results to within-module dependencies"),
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Get cross-file function-level dependencies for a specific file.

    Returns which functions in the given file call functions in other files.
    Only cross-file calls are included (same-file internal calls excluded).

    Use this when writing DETAIL docs to describe dependency relationships.
    """
    project_dir = resolve_project_dir(output_dir)

    deps_path = project_dir / "06_function_deps.json"
    if not deps_path.exists():
        raise ToolError(
            "Function deps not found. Re-run analyze_codebase with force_reindex=true."
        )

    deps_data = json.loads(deps_path.read_text(encoding="utf-8"))
    function_deps = deps_data.get("function_deps", {})

    file_deps = function_deps.get(file)
    if file_deps is None:
        return {
            "status": "success",
            "file": file,
            "dependencies": [],
            "message": "No cross-file function dependencies found for this file",
        }

    # Optional: filter to within-module deps
    if module_id:
        cones_path = project_dir / "03_feature_cones.json"
        if cones_path.exists():
            cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
            cone = cones_data.get("cones", {}).get(module_id)
            if cone:
                module_files = set(cone.get("exclusive_files", []))
                filtered = []
                for dep_entry in file_deps:
                    filtered_calls = [
                        c for c in dep_entry["calls"]
                        if c["target_file"] in module_files
                    ]
                    if filtered_calls:
                        filtered.append({
                            "source_function": dep_entry["source_function"],
                            "calls": filtered_calls,
                        })
                file_deps = filtered

    return {
        "status": "success",
        "file": file,
        "dependencies": file_deps,
    }


# ---------------------------------------------------------------------------
# Tool 3d: doc_operation (V5)
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False})
async def doc_operation(
    operation: Annotated[
        Literal[
            "get_template", "get_protocol",
            "render_semantic_docs",
            "move_detail", "merge_modules", "split_module", "list_module_files",
            "update_index", "reorder_modules",
        ],
        Field(description=(
            "Operation: 'get_template'/'get_protocol' for format info, "
            "'render_semantic_docs' to repair the semantic projection, "
            "'move_detail'/'merge_modules'/'split_module'/'list_module_files'/"
            "'update_index'/'reorder_modules' for doc editing"
        )),
    ],
    source_module: Annotated[
        str | None, Field(description="Source module ID (for move_detail, merge_modules, split_module)"),
    ] = None,
    target_module: Annotated[
        str | None, Field(description="Target module ID (for move_detail, merge_modules)"),
    ] = None,
    file_path: Annotated[
        str | None, Field(description="File path to move (for move_detail)"),
    ] = None,
    new_order: Annotated[
        list[str] | None, Field(description="Ordered list of module IDs (for reorder_modules)"),
    ] = None,
    params: Annotated[
        dict | None, Field(description="Additional parameters (for move_detail block-level: source_module, target_module, filepath)"),
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Documentation operations for DETAIL/INDEX generation and Phase 5 reorganization.

    Read-only operations:
    - get_template: Returns DETAIL format with four sections per file
    - get_protocol: Returns the three-step documentation protocol

    Semantic projection repair:
    - render_semantic_docs: Rebuild four-layer docs from the canonical ledger

    Editing operations (Phase 5 -- doc reorganization without manual text editing):
    - move_detail: Move a file block from one module's DETAIL.md to another's
    - merge_modules: Merge two modules into one (combines their DETAIL docs)
    - split_module / list_module_files: List files in a module directory
    - update_index: Regenerate INDEX.md from DETAIL.md index-fragment blocks
    - reorder_modules: Change the order of modules in INDEX
    """
    if operation == "get_template":
        detail_format = (
            "---\n"
            "module_id: {module_id}\n"
            "module_name: {module_name}\n"
            "file_count: N\n"
            "token_budget: {budget}\n"
            "generated_at: {timestamp}\n"
            "---\n"
            "\n"
            "<!-- module:{module_id} -->\n"
            "\n"
            "## {module_name}\n"
            "\n"
            "### {filename}\n"
            "<!-- file:{filepath} -->\n"
            "\n"
            "#### 功能概述 (Purpose)\n"
            "[What this file does and why it exists]\n"
            "\n"
            "#### 数据流 (Data Flow)\n"
            "[How data enters, transforms, and exits this file]\n"
            "\n"
            "#### 核心接口 (Key Interfaces)\n"
            "[Important functions/classes with signatures and brief descriptions]\n"
            "\n"
            "#### 依赖关系 (Dependencies)\n"
            "[Cross-file dependencies with specific function names and purposes]\n"
            "\n"
            "<!-- end:file:{filepath} -->\n"
            "\n"
            "<!-- index-fragment:{module_id} -->\n"
            "[2-3 sentence summary of this module for INDEX.md]\n"
            "<!-- end:index-fragment:{module_id} -->\n"
            "\n"
            "<!-- end:{module_id} -->\n"
            "<!-- codebase-explorer: end -->"
        )

        return {
            "status": "success",
            "detail_template": detail_format,
            "html_markers": {
                "module_start": "<!-- module:{module_id} -->",
                "module_end": "<!-- end:{module_id} -->",
                "file_start": "<!-- file:{filepath} -->",
                "file_end": "<!-- end:file:{filepath} -->",
                "index_fragment_start": "<!-- index-fragment:{module_id} -->",
                "index_fragment_end": "<!-- end:index-fragment:{module_id} -->",
            },
            "sections_per_file": [
                "#### 功能概述 (Purpose)",
                "#### 数据流 (Data Flow)",
                "#### 核心接口 (Key Interfaces)",
                "#### 依赖关系 (Dependencies)",
            ],
            "index_template": {
                "yaml_front_matter": (
                    "---\ntitle: {project_name} Architecture\n"
                    "generated: {timestamp}\nmodule_count: {N}\n---"
                ),
                "assembly_rule": (
                    "INDEX is assembled by extracting index-fragment blocks from all "
                    "DETAIL.md files. No separate agent rewrites the INDEX."
                ),
            },
        }

    if operation == "get_protocol":
        return {
            "status": "success",
            "detail_protocol": {
                "name": "Three-Step Documentation Protocol",
                "steps": [
                    {
                        "step": 1,
                        "name": "Read source code, write four sections per file",
                        "description": (
                            "For each file in the module:\n"
                            "  a. Read the source code\n"
                            "  b. Write: Purpose, Data Flow, Key Interfaces, Dependencies"
                        ),
                        "tool": "Read source file directly",
                    },
                    {
                        "step": 2,
                        "name": "Query function dependencies",
                        "description": (
                            "Call get_function_deps(file=filepath) for key files. "
                            "Integrate cross-file dependency info into the Dependencies section."
                        ),
                        "tool": "get_function_deps",
                    },
                    {
                        "step": 3,
                        "name": "Write index fragment",
                        "description": (
                            "At the end of DETAIL.md, write <!-- index-fragment:{module_id} --> block. "
                            "Include a 2-3 sentence summary of the module's purpose. "
                            "This fragment will be extracted by update_index to build INDEX.md."
                        ),
                        "tool": "Agent writes index-fragment block",
                    },
                ],
                "token_budget_rule": (
                    "Before reading each file, check: accumulated_tokens + file_token_count <= budget. "
                    "If the next file would exceed the budget, STOP. Write INDEX fragment for completed files. "
                    "Track accumulated_tokens as running sum of token_count for each file read."
                ),
            },
        }

    if operation == "render_semantic_docs":
        repo_root = _semantic_repo_root(output_dir)
        try:
            service = _semantic_service(repo_root)
            result = service.render_semantic_docs()
        except (SemanticServiceError, OSError, ValueError) as exc:
            raise ToolError(f"Semantic document repair failed: {exc}") from exc
        return {
            "status": "success",
            "operation": "render_semantic_docs",
            "repaired": True,
            **dict(result),
        }

    # --- CRUD operations for Phase 5 doc reorganization ---
    project_dir = resolve_project_dir(output_dir)
    analysis_root = _analysis_root_for_generation(project_dir)
    canonical_state_path = project_dir / "state-v3.json"
    canonical_snapshot = None
    if canonical_state_path.exists():
        canonical_snapshot = JsonRunStore(canonical_state_path).snapshot()
        state = {"path": canonical_snapshot.repo_root}
        state_path = analysis_root / "state.json"
    else:
        state_path = project_dir / "state.json"
        state = read_state(state_path) if state_path.exists() else {}

    # Resolve doc_dir: sibling of .codebase-analysis -> .codebase-docs
    analysis_dir = Path(state.get("path", "")) if state.get("path") else project_dir.parent
    doc_dir = analysis_dir / ".codebase-docs"

    # Load or initialize doc-index.json
    doc_index_path = doc_dir / "doc-index.json"
    doc_index: dict = {}
    if doc_index_path.exists():
        doc_index = json.loads(doc_index_path.read_text(encoding="utf-8"))

    def _save_doc_index() -> None:
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_index_path.write_text(
            json.dumps(doc_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if operation == "move_detail":
        # Block-level move: extract a file block from source DETAIL.md,
        # insert into target DETAIL.md
        p = params or {}
        src_mod = p.get("source_module") or source_module
        tgt_mod = p.get("target_module") or target_module
        fp = p.get("filepath") or file_path

        if not all([src_mod, tgt_mod, fp]):
            raise ToolError(
                "move_detail requires source_module, target_module, and filepath"
            )

        src_detail = doc_dir / src_mod / "DETAIL.md"
        tgt_detail = doc_dir / tgt_mod / "DETAIL.md"

        if not src_detail.exists():
            raise ToolError(f"Source DETAIL.md not found: {src_detail}")

        src_content = src_detail.read_text(encoding="utf-8")

        # Extract the file block (including any preceding heading + separator)
        # Matches: optional "---\n\n### filepath\n" + <!-- file:xxx -->...<!-- end:file:xxx -->
        block_pattern = re.compile(
            rf"(?:---\s*\n+###\s+{re.escape(fp)}\s*\n)?"
            rf"(<!-- file:{re.escape(fp)} -->.*?<!-- end:file:{re.escape(fp)} -->)",
            re.DOTALL,
        )
        match = block_pattern.search(src_content)
        if not match:
            raise ToolError(
                f"File block '<!-- file:{fp} -->' not found in {src_detail}"
            )

        extracted_block = match.group(1)

        # Remove the entire matched region (heading + block) from source
        new_src_content = src_content[:match.start()] + src_content[match.end():]
        # Clean up multiple blank lines
        new_src_content = re.sub(r"\n{3,}", "\n\n", new_src_content).strip() + "\n"
        # Update source YAML front matter file_count
        src_file_count = len(re.findall(r"<!-- file:", new_src_content))
        new_src_content = re.sub(
            r"(file_count:\s*)\d+",
            rf"\g<1>{src_file_count}",
            new_src_content,
            count=1,
        )
        src_detail.write_text(new_src_content, encoding="utf-8")

        # Insert block into target DETAIL.md
        tgt_dir = doc_dir / tgt_mod
        tgt_dir.mkdir(parents=True, exist_ok=True)

        if tgt_detail.exists():
            tgt_content = tgt_detail.read_text(encoding="utf-8")
            # Insert before the index-fragment marker
            idx_frag_pos = tgt_content.find("<!-- index-fragment:")
            if idx_frag_pos >= 0:
                tgt_content = (
                    tgt_content[:idx_frag_pos]
                    + extracted_block + "\n\n"
                    + tgt_content[idx_frag_pos:]
                )
            else:
                # Append before end marker
                end_pos = tgt_content.find("<!-- codebase-explorer: end -->")
                if end_pos >= 0:
                    tgt_content = (
                        tgt_content[:end_pos]
                        + extracted_block + "\n\n"
                        + tgt_content[end_pos:]
                    )
                else:
                    tgt_content += "\n" + extracted_block + "\n"
        else:
            tgt_content = extracted_block + "\n"

        # Update target YAML front matter file_count
        tgt_file_count = len(re.findall(r"<!-- file:", tgt_content))
        tgt_content = re.sub(
            r"(file_count:\s*)\d+",
            rf"\g<1>{tgt_file_count}",
            tgt_content,
            count=1,
        )
        tgt_detail.write_text(tgt_content, encoding="utf-8")

        return {
            "status": "success",
            "operation": "move_detail",
            "moved": fp,
            "from_module": src_mod,
            "to_module": tgt_mod,
            "message": f"Moved file block '{fp}' from {src_mod}/DETAIL.md to {tgt_mod}/DETAIL.md",
        }

    if operation == "merge_modules":
        if not all([source_module, target_module]):
            raise ToolError("merge_modules requires source_module and target_module")

        src_dir = doc_dir / source_module
        tgt_dir = doc_dir / target_module
        tgt_dir.mkdir(parents=True, exist_ok=True)

        moved_files: list[str] = []
        if src_dir.exists():
            import shutil
            for item in src_dir.iterdir():
                dest = tgt_dir / item.name
                if item.is_file():
                    shutil.move(str(item), str(dest))
                    moved_files.append(item.name)
                elif item.is_dir():
                    if dest.exists():
                        # Merge subdirectory contents
                        for sub_item in item.iterdir():
                            shutil.move(str(sub_item), str(dest / sub_item.name))
                        item.rmdir()
                    else:
                        shutil.move(str(item), str(dest))
                    moved_files.append(item.name + "/")
            # Remove empty source directory
            if src_dir.exists() and not any(src_dir.iterdir()):
                src_dir.rmdir()

        # Update doc-index.json
        docs = doc_index.get("documents", [])
        for d in docs:
            if d.get("module") == source_module:
                d["module"] = target_module
                old_prefix = source_module + "/"
                new_prefix = target_module + "/"
                if d.get("path", "").startswith(old_prefix):
                    d["path"] = new_prefix + d["path"][len(old_prefix):]
        doc_index["documents"] = docs
        _save_doc_index()

        return {
            "status": "success",
            "operation": "merge_modules",
            "merged": source_module,
            "into": target_module,
            "moved_files": moved_files,
            "message": f"Merged {source_module} into {target_module}. {len(moved_files)} items moved.",
        }

    if operation in ("split_module", "list_module_files"):
        if operation == "split_module":
            logger.info("[doc_operation] 'split_module' is deprecated, use 'list_module_files'")
        if not source_module:
            raise ToolError(f"{operation} requires source_module")

        src_dir = doc_dir / source_module
        if not src_dir.exists():
            raise ToolError(f"Module directory not found: {src_dir}")

        files_in_module = [
            str(f.relative_to(src_dir)) for f in src_dir.rglob("*") if f.is_file()
        ]

        return {
            "status": "success",
            "operation": operation,
            "source_module": source_module,
            "files": files_in_module,
            "message": (
                f"Module {source_module} contains {len(files_in_module)} files. "
                "Use move_detail to reassign files to a new module."
            ),
        }

    if operation == "update_index":
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Scan all DETAIL.md files for <!-- index-fragment:xxx --> blocks
        _INDEX_FRAGMENT_RE = re.compile(
            r"<!-- index-fragment:(\S+?) -->(.*?)<!-- end:index-fragment:\S+? -->",
            re.DOTALL,
        )

        detail_fragments: dict[str, str] = {}
        module_display_names: dict[str, str] = {}  # module_id → functional name
        _YAML_NAME_RE = re.compile(r"^module_name:\s*(.+)$", re.MULTILINE)
        module_dirs = sorted(
            [d for d in doc_dir.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )

        for mod_dir in module_dirs:
            for detail_file in sorted(mod_dir.rglob("DETAIL.md")):
                content = detail_file.read_text(encoding="utf-8")
                # Extract module_name from YAML front matter
                name_match = _YAML_NAME_RE.search(content)
                if name_match:
                    module_display_names[mod_dir.name] = name_match.group(1).strip()
                for m in _INDEX_FRAGMENT_RE.finditer(content):
                    frag_module_id = m.group(1)
                    frag_content = m.group(2).strip()
                    if frag_content:
                        detail_fragments[frag_module_id] = frag_content

        # Determine module ordering:
        # 1. Use doc-index order if available
        # 2. Use cone data layer ordering if available
        # 3. Alphabetical fallback
        ordered_modules = doc_index.get("module_order", [])

        # Try to get cone ordering from analysis data
        cone_order: dict[str, int] = {}
        cones_path = project_dir / "03_feature_cones.json"
        project_name = "Project"
        total_modules = 0
        if cones_path.exists():
            cd = json.loads(cones_path.read_text(encoding="utf-8"))
            total_modules = cd.get("cone_count", 0)
            project_name = Path(state.get("path", "Project")).name
            for cid, cone in cd.get("cones", {}).items():
                cone_order[cid] = cone.get("layer", 0)

        # Build sorted module ID list
        all_module_ids = sorted(
            set(list(detail_fragments.keys()) + [d.name for d in module_dirs]),
        )
        if ordered_modules:
            # Use explicit order, then append any missing
            sorted_module_ids = [m for m in ordered_modules if m in all_module_ids]
            for mid in all_module_ids:
                if mid not in sorted_module_ids:
                    sorted_module_ids.append(mid)
        elif cone_order:
            sorted_module_ids = sorted(all_module_ids, key=lambda m: cone_order.get(m, 999))
        else:
            sorted_module_ids = all_module_ids

        # Build module-level Mermaid graph
        mermaid_block = ""
        dag_path = project_dir / "02_dag.json"
        if dag_path.exists() and cones_path.exists():
            dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
            cd = json.loads(cones_path.read_text(encoding="utf-8"))
            mod_graph = build_module_level_graph(
                cd.get("cones", {}),
                dag_data.get("edges", []),
                infrastructure_files=cd.get("infrastructure_files", []),
            )
            mermaid_block = (
                "\n```mermaid\n"
                + render_mermaid(
                    mod_graph,
                    include_weights=True,
                    labels=module_display_names,
                )
                + "\n```\n"
            )

        # Build INDEX.md content
        fragments_content: list[str] = []
        for mid in sorted_module_ids:
            frag = detail_fragments.get(mid, "")
            heading = module_display_names.get(mid, mid)
            fragments_content.append(f"<!-- module-index:{mid} -->")
            fragments_content.append(f"## {heading}")
            if frag:
                fragments_content.append(frag)
            fragments_content.append(f"[→ DETAIL]({mid}/DETAIL.md)")
            fragments_content.append(f"<!-- end-module-index:{mid} -->")
            fragments_content.append("")

        ts = now_iso()
        index_content = (
            f"---\ntitle: {project_name} Architecture\n"
            f"generated: {ts}\n"
            f"module_count: {total_modules}\n"
            f"---\n\n"
            f"# {project_name} Architecture\n"
            f"{mermaid_block}\n"
            + "\n".join(fragments_content)
            + "\n<!-- codebase-explorer: end -->\n"
        )

        index_path = doc_dir / "INDEX.md"
        index_path.write_text(index_content, encoding="utf-8")

        # Update doc-index.json
        doc_index["index_path"] = "INDEX.md"
        doc_index["module_count"] = len(sorted_module_ids)
        _save_doc_index()

        if canonical_snapshot is not None:
            actor = "orchestrator/legacy-mcp/doc_operation:update_index"
            producer = "legacy-mcp/doc_operation:update_index"
            store = JsonRunStore(canonical_state_path)
            parent = _route_parent(
                canonical_snapshot,
                target="capability:route-parent:doc_operation:update_index",
                actor=actor,
            )
            try:
                leased = store.lease_task(
                    run_id=canonical_snapshot.run_id,
                    target="index",
                    actor=actor,
                    lease_id=parent.lease_id,
                    expected_revision=canonical_snapshot.store_revision,
                )
                index_bytes = index_path.read_bytes()
                store.submit_artifact(
                    run_id=canonical_snapshot.run_id,
                    target="index",
                    actor=actor,
                    producer=producer,
                    lease_id=leased.lease.lease_id,
                    expected_revision=leased.snapshot.store_revision,
                    artifact_bytes=index_bytes,
                    artifact_hash=hashlib.sha256(index_bytes).hexdigest(),
                    revision_kind="document",
                )
            except RunStoreError as exc:
                raise ToolError(
                    f"Canonical update-index state commit failed for run "
                    f"{canonical_snapshot.run_id} at revision "
                    f"{canonical_snapshot.store_revision}; regenerate after refreshing: {exc}"
                ) from exc

        return {
            "status": "success",
            "operation": "update_index",
            "index_path": str(index_path),
            "module_count": len(sorted_module_ids),
            "fragments_found": len(detail_fragments),
            "message": f"INDEX.md regenerated from {len(detail_fragments)} DETAIL.md index fragments.",
        }

    if operation == "reorder_modules":
        if not new_order:
            raise ToolError("reorder_modules requires new_order (list of module IDs)")

        doc_index["module_order"] = new_order
        _save_doc_index()

        return {
            "status": "success",
            "operation": "reorder_modules",
            "new_order": new_order,
            "message": "Module order saved. Call update_index to apply.",
        }

    return {"status": "error", "message": f"Unknown operation: {operation}"}


# ---------------------------------------------------------------------------
# Tool 4: get_dependency_graph
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_dependency_graph(
    scope: Annotated[
        Literal["project", "cone", "module", "file"],
        Field(description="Scope: 'project', 'cone'/'module' (aliases), or 'file'"),
    ] = "project",
    target: Annotated[
        str | None,
        Field(description="Cone ID or file path (required for scope=cone/file)"),
    ] = None,
    include_weights: Annotated[
        bool, Field(description="Include edge weights in diagram")
    ] = False,
    hops: Annotated[
        int, Field(description="N-hop neighbors for scope=file (default 1)")
    ] = 1,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Generate Mermaid dependency graph from 02_dag.json.

    Scopes:
    - project: Full DAG dependency graph (all nodes and edges)
    - cone: File-level graph within a specific feature cone
    - file: N-hop neighbor subgraph centered on a single file

    include_weights=True annotates edges with weight and relationship type.
    """
    # Normalize scope: "module" is an alias for "cone"
    if scope == "module":
        scope = "cone"

    logger.info("[DEP-GRAPH] Generating dependency graph scope=%s", scope)

    project_dir = resolve_project_dir(output_dir)

    dag_path = project_dir / "02_dag.json"
    if not dag_path.exists():
        raise ToolError(f"DAG file not found: {dag_path}")

    dag_data = json.loads(dag_path.read_text(encoding="utf-8"))

    # --- Reconstruct NetworkX graph from persisted DAG data ---------------
    all_nodes: list[str] = dag_data.get("nodes", [])
    all_edges: list[dict] = dag_data.get("edges", [])

    graph = build_graph_from_dag(all_nodes, all_edges)

    # --- Detect circular dependencies (SCC with >1 member) ---------------
    circular_deps = [
        sorted(scc)
        for scc in nx.strongly_connected_components(graph)
        if len(scc) > 1
    ]

    # --- Extract subgraph based on scope ----------------------------------
    if scope == "project":
        # Module-level aggregated graph (not file-level)
        cones_path = project_dir / "03_feature_cones.json"
        if cones_path.exists():
            cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
            cones_dict = cones_data.get("cones", {})
            if cones_dict:
                subgraph = build_module_level_graph(cones_dict, all_edges)
                mermaid_graph = render_mermaid(subgraph, include_weights=include_weights)
                result_nodes = sorted(subgraph.nodes())
                result_edges = [
                    {
                        "source": u,
                        "target": v,
                        "weight": data.get("weight", 1),
                        "edge_types": data.get("edge_types", []),
                    }
                    for u, v, data in sorted(subgraph.edges(data=True))
                ]
                return {
                    "status": "success",
                    "scope": scope,
                    "target": target,
                    "level": "module",
                    "mermaid_graph": mermaid_graph,
                    "nodes": result_nodes,
                    "edges": result_edges,
                    "node_count": subgraph.number_of_nodes(),
                    "edge_count": subgraph.number_of_edges(),
                    "circular_deps": [],
                }
        # Fallback: full file-level graph if no cones
        subgraph = graph

    elif scope == "cone":
        if not target:
            raise ToolError("target (cone_id) is required when scope='cone'")

        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError(f"Feature cones file not found: {cones_path}")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(target)
        if not cone:
            raise ToolError(f"Cone '{target}' not found")

        # Collect all files relevant to this cone: exclusive + shared_deps
        cone_files = set(cone.get("exclusive_files", []))
        cone_files.update(cone.get("shared_deps", []))
        valid_nodes = [n for n in cone_files if n in graph]
        subgraph = graph.subgraph(valid_nodes).copy()

    elif scope == "file":
        if not target:
            raise ToolError("target (file_path) is required when scope='file'")

        if target not in graph:
            raise ToolError(f"File '{target}' not found in dependency graph")

        # Collect N-hop neighbors (both predecessors and successors)
        clamped_hops = max(1, min(hops, MAX_HOPS))
        nodes_to_include = {target}
        frontier = {target}
        for _ in range(clamped_hops):
            new_frontier = set()
            for node in frontier:
                new_frontier.update(graph.predecessors(node))
                new_frontier.update(graph.successors(node))
            nodes_to_include.update(new_frontier)
            frontier = new_frontier

        subgraph = graph.subgraph(nodes_to_include).copy()

    else:
        raise ToolError(f"Invalid scope: {scope}")

    # --- Build Mermaid diagram from subgraph ------------------------------
    mermaid_graph = render_mermaid(subgraph, include_weights=include_weights)

    # --- Build structured node and edge lists for the response ------------
    result_nodes = sorted(subgraph.nodes())
    result_edges = [
        {
            "source": u,
            "target": v,
            "weight": data.get("weight", 1),
            "edge_types": data.get("edge_types", []),
        }
        for u, v, data in sorted(subgraph.edges(data=True))
    ]

    node_count = subgraph.number_of_nodes()
    edge_count = subgraph.number_of_edges()

    logger.info(
        "[DEP-GRAPH] Graph generated: %d nodes, %d edges",
        node_count,
        edge_count,
    )

    return {
        "status": "success",
        "scope": scope,
        "target": target,
        "mermaid_graph": mermaid_graph,
        "nodes": result_nodes,
        "edges": result_edges,
        "node_count": node_count,
        "edge_count": edge_count,
        "circular_deps": circular_deps,
    }


# ---------------------------------------------------------------------------
# Tool 5: get_progress
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_progress(
    project_id: Annotated[
        str | None, Field(description="Project ID. None = latest project.")
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Project the existing progress shape from the selected canonical V3 run."""
    project_dir = resolve_project_dir(output_dir)
    state_path = project_dir / "state-v3.json"
    if not state_path.exists():
        raise ToolError(f"Canonical state file not found: {state_path}")
    try:
        snapshot = JsonRunStore(state_path).snapshot()
    except RecoveryError as exc:
        raise ToolError(f"Failed to read canonical state: {exc}") from exc
    legacy = snapshot.legacy_submission
    if legacy is None:
        raise ToolError("Canonical legacy progress is not initialized")

    total = len(legacy.tasks)
    pending = sum(1 for task in legacy.tasks if task.status == "pending")
    complete = sum(1 for task in legacy.tasks if task.status == "complete")
    in_progress = 0
    failed = 0

    progress_percent = (complete / total * 100) if total > 0 else 0.0

    next_pending = [task.task_id for task in legacy.tasks if task.status == "pending"][:10]
    completed = tuple(task for task in legacy.tasks if task.status == "complete")
    metadata = legacy.projection_metadata
    coverage = (
        len(metadata.source_files_covered) / metadata.source_file_count * 100
        if metadata.source_file_count
        else 0.0
    )
    index_written = any(
        artifact.target == "index"
        and artifact.actor == "orchestrator/legacy-mcp/doc_operation:update_index"
        and artifact.producer == "legacy-mcp/doc_operation:update_index"
        for artifact in snapshot.artifacts
    )

    return {
        "status": "success",
        "project_id": snapshot.metadata.get("project_id"),
        "tasks": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "complete": complete,
            "failed": failed,
            "progress_percent": round(progress_percent, 2),
        },
        "documentation": {
            "output_dir": snapshot.metadata.get("analysis_root", ""),
            "index_written": index_written,
            "details_written": sum(task.details_written for task in completed),
            "snippets_written": sum(task.snippets_written for task in completed),
            "total_planned": total,
            "source_file_coverage_percent": coverage,
        },
        "next_pending_tasks": next_pending,
    }


# ---------------------------------------------------------------------------
# Tool 6: get_file_tokens
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
async def get_file_tokens(
    file: Annotated[str | None, Field(description="File path. None = all files.")] = None,
    module: Annotated[
        str | None, Field(description="Module/cone ID. None = all modules.")
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Query file token estimates from 04_file_tokens.json."""
    project_dir = resolve_project_dir(output_dir)

    tokens_path = project_dir / "04_file_tokens.json"
    if not tokens_path.exists():
        raise ToolError(f"Tokens file not found: {tokens_path}")

    tokens_data = json.loads(tokens_path.read_text(encoding="utf-8"))
    files = tokens_data.get("files", [])

    # Mode: All files — return top 20 by token count + summary
    if not file and not module:
        sorted_files = sorted(files, key=lambda f: f.get("estimated_tokens", 0), reverse=True)
        top_files = sorted_files[:20]
        return {
            "status": "success",
            "total_tokens": tokens_data.get("total_tokens", 0),
            "file_count": tokens_data.get("file_count", 0),
            "top_files": top_files,
            "showing": min(20, len(files)),
            "hint": "Use module= to see all files in a specific module." if len(files) > 20 else None,
        }

    # Mode: Single file
    if file:
        file_info = next((f for f in files if f["filepath"] == file), None)
        if not file_info:
            raise ToolError(f"File not found: {file}")

        return {
            "status": "success",
            "filepath": file_info["filepath"],
            "language": file_info.get("language", "unknown"),
            "char_count": file_info.get("char_count", 0),
            "line_count": file_info.get("line_count", 0),
            "estimated_tokens": file_info.get("estimated_tokens", 0),
            "method": file_info.get("method", "unknown"),
            "cone_id": file_info.get("cone_id"),
        }

    # Mode: Module/Cone
    if module:
        # Load cone data to get files
        cones_path = project_dir / "03_feature_cones.json"
        if not cones_path.exists():
            raise ToolError("Feature cones file not found")

        cones_data = json.loads(cones_path.read_text(encoding="utf-8"))
        cone = cones_data.get("cones", {}).get(module)
        if not cone:
            raise ToolError(f"Module/cone '{module}' not found")

        cone_files = [
            f
            for f in files
            if f["filepath"] in cone.get("exclusive_files", [])
        ]

        total = sum(f.get("estimated_tokens", 0) for f in cone_files)
        max_tokens = max((f.get("estimated_tokens", 0) for f in cone_files), default=0)

        return {
            "status": "success",
            "cone_id": module,
            "file_count": len(cone_files),
            "total_tokens": total,
            "avg_tokens_per_file": (total / len(cone_files)) if cone_files else 0.0,
            "max_file_tokens": max_tokens,
            "files": cone_files,
        }

    raise ToolError("Invalid query parameters")


# ---------------------------------------------------------------------------
# Tool 7: submit_analysis
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": False})
async def submit_analysis(
    task_id: Annotated[str, Field(description="Task ID from task_manifest")],
    detail_paths: Annotated[
        list[str], Field(description="Paths to written DETAIL.md files")
    ],
    snippet_paths: Annotated[
        list[str], Field(description="Paths to written SNIPPET.md files")
    ],
    tokens_used: Annotated[int, Field(description="Tokens consumed")],
    source_files_covered: Annotated[
        list[str] | None,
        Field(description="Source files covered by this analysis"),
    ] = None,
    project_id: Annotated[
        str | None, Field(description="Project ID. None = latest.")
    ] = None,
    output_dir: Annotated[str | None, Field(description="Path to .codebase-analysis/ dir. Auto-detects if omitted.")] = None,
) -> dict:
    """Submit one legacy analysis through the canonical atomic V3 ingress.

    Called by DETAIL Agent after writing documentation files.
    Atomically updates task, artifact and legacy projection inputs.
    """
    project_dir = resolve_project_dir(output_dir)
    state_path = project_dir / "state-v3.json"
    if not state_path.exists():
        raise ToolError(f"Canonical state file not found: {state_path}")
    store = JsonRunStore(state_path)
    try:
        snapshot = store.snapshot()
    except RecoveryError as exc:
        raise ToolError(f"Canonical state is unavailable: {exc}") from exc
    project_root = Path(snapshot.repo_root).parent

    # Verify files exist, validate paths are within project directory, and append end marker
    end_marker = "\n<!-- codebase-explorer: end -->\n"
    for path in detail_paths + snippet_paths:
        p = Path(path).resolve()
        if not p.is_relative_to(project_root):
            raise ToolError(f"Path traversal rejected — file is outside project directory: {path}")
        if not p.exists():
            raise ToolError(f"File not found: {path}")
        content = p.read_text(encoding="utf-8")
        if "<!-- codebase-explorer: end -->" not in content:
            p.write_text(content + end_marker, encoding="utf-8")

    receipt_payload = {
        "schema": "cbe-legacy-submission-receipt-1",
        "task_id": task_id,
        "tokens_used": tokens_used,
        "detail_files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in detail_paths
        ],
        "snippet_files": [
            {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            for path in snippet_paths
        ],
    }
    receipt_bytes = (
        json.dumps(receipt_payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    actor = "orchestrator/legacy-mcp/submit_analysis"
    parent = _route_parent(
        snapshot,
        target="capability:route-parent:submit_analysis",
        actor=actor,
    )
    try:
        leased = store.lease_task(
            run_id=snapshot.run_id,
            target=task_id,
            actor=actor,
            lease_id=parent.lease_id,
            expected_revision=snapshot.store_revision,
        )
        submitted = store.submit_legacy_analysis(
            run_id=snapshot.run_id,
            task_id=task_id,
            actor=actor,
            producer="legacy-mcp/submit_analysis",
            lease_id=leased.lease.lease_id,
            expected_revision=leased.snapshot.store_revision,
            artifact_bytes=receipt_bytes,
            artifact_hash=hashlib.sha256(receipt_bytes).hexdigest(),
            details_written=len(detail_paths),
            snippets_written=len(snippet_paths),
            source_files_covered=tuple(source_files_covered or ()),
        )
    except RunStoreError as exc:
        current_revision = store.snapshot().store_revision
        raise ToolError(
            f"Canonical submit failed for run {snapshot.run_id}; "
            f"expected_revision={snapshot.store_revision}, "
            f"current_revision={current_revision}; refresh progress and retry: {exc}"
        ) from exc
    projection = submitted.projection

    return {
        "status": projection.status,
        "task_id": projection.task_id,
        "tasks_remaining": projection.tasks_remaining,
        "progress_percent": projection.progress_percent,
        "source_file_coverage_percent": projection.source_file_coverage_percent,
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
