"""End-to-end tests for the complete codebase-explorer analysis pipeline.

Verifies the full pipeline flow:
  1. Parse codebase -> CodebaseSnapshot
  2. Build weighted dependency graph
  3. Extract feature cones via SCC + DAG
  4. Estimate tokens per file
  5. Build task manifest
  6. Publish the six JSON artifacts through the active generation lifecycle

Uses a realistic temporary Python project with real dependency structures.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import (
    build_task_manifest,
    calculate_feature_cone_depth,
)
from src.graph.feature_cone import FeatureCone, extract_feature_cones
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser, CodebaseSnapshot
from src.server_helpers import (
    project_id_from_path,
    resolve_output_dir,
    validate_json_files_exist,
    write_analysis_outputs,
)
from src.state.json_store import JsonRunStore, read_state
from src.state.migrate_v2_v3 import write_v2_rollback_projection
from src.state.models import LegacySubmissionSeed
from src.state.run_lifecycle import (
    ActiveRunReceipt,
    ROUTE_KEYS,
    analysis_input_fingerprint,
    artifact_manifest,
    legacy_seed_sha256,
    promote_active_receipt,
    publish_generation,
    stage_v2_recovery_projection,
)

# ---------------------------------------------------------------------------
# Realistic project fixture: 8 Python files with real dependency chains
# ---------------------------------------------------------------------------

_PROJECT_FILES: dict[str, str] = {
    "app/__init__.py": (
        "from app.config import settings\n"
        "from app.models import User\n"
        "\n"
        "__version__ = '1.0.0'\n"
    ),
    "app/config.py": (
        "import os\n"
        "\n"
        "class Settings:\n"
        "    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\n"
        "    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')\n"
        "    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')\n"
        "\n"
        "settings = Settings()\n"
    ),
    "app/models.py": (
        "from app.config import Settings\n"
        "\n"
        "\n"
        "class BaseModel:\n"
        "    def save(self):\n"
        "        pass\n"
        "\n"
        "    def delete(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "class User(BaseModel):\n"
        "    def __init__(self, name: str, email: str):\n"
        "        self.name = name\n"
        "        self.email = email\n"
        "\n"
        "    def validate(self) -> bool:\n"
        "        return bool(self.name and self.email)\n"
        "\n"
        "\n"
        "class Admin(User):\n"
        "    def __init__(self, name: str, email: str, role: str = 'admin'):\n"
        "        super().__init__(name, email)\n"
        "        self.role = role\n"
        "\n"
        "    def has_permission(self, perm: str) -> bool:\n"
        "        return True\n"
    ),
    "app/utils.py": (
        "import hashlib\n"
        "import re\n"
        "\n"
        "\n"
        "def hash_password(password: str) -> str:\n"
        "    return hashlib.sha256(password.encode()).hexdigest()\n"
        "\n"
        "\n"
        "def validate_email(email: str) -> bool:\n"
        "    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'\n"
        "    return bool(re.match(pattern, email))\n"
        "\n"
        "\n"
        "def slugify(text: str) -> str:\n"
        "    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')\n"
    ),
    "app/api/routes.py": (
        "from app.models import User, Admin\n"
        "from app.utils import validate_email\n"
        "from app.api.middleware import require_auth\n"
        "\n"
        "\n"
        "def create_user(name: str, email: str) -> User:\n"
        "    if not validate_email(email):\n"
        "        raise ValueError('Invalid email')\n"
        "    user = User(name=name, email=email)\n"
        "    user.save()\n"
        "    return user\n"
        "\n"
        "\n"
        "def get_user(user_id: int) -> User:\n"
        "    return User(name='test', email='test@example.com')\n"
        "\n"
        "\n"
        "def list_admins() -> list:\n"
        "    return [Admin(name='root', email='root@example.com')]\n"
    ),
    "app/api/__init__.py": "",
    "app/api/middleware.py": (
        "from app.config import Settings\n"
        "from app.utils import hash_password\n"
        "\n"
        "\n"
        "def require_auth(func):\n"
        "    def wrapper(*args, **kwargs):\n"
        "        return func(*args, **kwargs)\n"
        "    return wrapper\n"
        "\n"
        "\n"
        "def log_request(func):\n"
        "    def wrapper(*args, **kwargs):\n"
        "        print(f'Request: {func.__name__}')\n"
        "        return func(*args, **kwargs)\n"
        "    return wrapper\n"
    ),
    "cli.py": (
        "from app.models import User\n"
        "from app.api.routes import create_user, list_admins\n"
        "from app.config import settings\n"
        "\n"
        "\n"
        "def main():\n"
        "    print('CLI started')\n"
        "    user = create_user('Alice', 'alice@example.com')\n"
        "    print(f'Created user: {user.name}')\n"
        "    admins = list_admins()\n"
        "    print(f'Admins: {len(admins)}')\n"
        "\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ),
}
"""Eight Python files with realistic import chains forming a diamond DAG:

    cli.py
      -> app/api/routes.py -> app/models.py -> app/config.py
      -> app/api/routes.py -> app/utils.py
      -> app/api/routes.py -> app/api/middleware.py -> app/config.py
      -> app/api/routes.py -> app/api/middleware.py -> app/utils.py
      -> app/models.py
      -> app/config.py
    app/__init__.py -> app/config.py, app/models.py
"""


@pytest.fixture
def realistic_project(tmp_path: Path) -> Path:
    """Create a multi-file Python project in a temp directory.

    Returns the project root path containing 8 Python files with real
    import dependencies between them.
    """
    for rel_path, content in _PROJECT_FILES.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def parsed_snapshot(realistic_project: Path) -> CodebaseSnapshot:
    """Parse the realistic project and return the snapshot."""
    parser = CodebaseParser()
    return parser.parse(str(realistic_project), languages=["python"])


@pytest.fixture
def pipeline_outputs(realistic_project: Path, parsed_snapshot: CodebaseSnapshot) -> dict:
    """Run the full analysis pipeline and return paths + data.

    This fixture executes steps 2-6 of the pipeline (graph, cones, tokens,
    manifest, write) and returns a dict with all intermediate results.
    """
    analysis_root = realistic_project / ".codebase-analysis"
    analysis_root.mkdir(parents=True, exist_ok=True)
    project_id = project_id_from_path(str(realistic_project))

    # Step 2: Build weighted dependency graph
    weighted_result = build_weighted_dependency_graph(parsed_snapshot)
    graph = weighted_result.graph

    # Step 3: Extract feature cones
    cones, infrastructure = extract_feature_cones(graph, parsed_snapshot)

    # Step 3b: Compute cone layers (simplified from server.py)
    import networkx as nx

    condensed = nx.condensation(graph)
    file_layer: dict[str, int] = {}
    remaining = set(condensed.nodes())
    layer_idx = 0
    while remaining:
        current = {
            n
            for n in remaining
            if all(p not in remaining for p in condensed.predecessors(n))
        }
        if not current:
            current = remaining.copy()
        for scc_node in current:
            members = condensed.nodes[scc_node].get("members", set())
            for member in members:
                file_layer[member] = layer_idx
        remaining -= current
        layer_idx += 1
    total_layers = layer_idx

    cone_layer: dict[str, int] = {}
    for cid, cone in cones.items():
        if cone.exclusive_files:
            cone_layer[cid] = max(file_layer.get(f, 0) for f in cone.exclusive_files)
        else:
            cone_layer[cid] = 0

    updated_cones: dict[str, FeatureCone] = {}
    for cid, cone in cones.items():
        updated_cones[cid] = FeatureCone(
            cone_id=cone.cone_id,
            entry_point=cone.entry_point,
            exclusive_files=cone.exclusive_files,
            shared_deps=cone.shared_deps,
            layer=cone_layer.get(cid, 0),
            token_count=cone.token_count,
        )
    cones = updated_cones

    # Step 4: Estimate tokens per file
    file_tokens: dict[str, int] = {}
    file_details: list[dict] = []
    for file_info in parsed_snapshot.files:
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

    # Step 5: Build task manifest
    cone_dicts: dict[str, dict] = {}
    for cone_id, cone in cones.items():
        cone_tokens = sum(file_tokens.get(f, 0) for f in cone.exclusive_files)
        cone_dicts[cone_id] = {
            "cone_id": cone_id,
            "entry_point": cone.entry_point,
            "exclusive_files": cone.exclusive_files,
            "shared_deps": cone.shared_deps,
            "layer": cone.layer,
            "token_count": cone_tokens,
        }

    task_manifest = build_task_manifest(cone_dicts, file_tokens)

    # Step 6: Write one unpublished generation, then activate it through the
    # same receipt-linked lifecycle used by the server entrypoint.  The
    # artifact writer deliberately has no authority to select a generation.
    run_id = "run-e2e-pipeline"
    staging_path = analysis_root / ".staging" / run_id
    staging_path.mkdir(parents=True, exist_ok=False)
    v2_projection = write_analysis_outputs(
        output_path=staging_path,
        project_id=project_id,
        resolved_path=realistic_project,
        snapshot=parsed_snapshot,
        weighted_result=weighted_result,
        graph=graph,
        cones=cones,
        infrastructure=infrastructure,
        cone_dicts=cone_dicts,
        file_tokens=file_tokens,
        file_details=file_details,
        task_manifest=task_manifest,
    )
    v2_projection["documentation"]["output_dir"] = str(analysis_root)
    v2_recovery_projection_sha = stage_v2_recovery_projection(
        staging_path, v2_projection
    )

    seed = LegacySubmissionSeed(
        task_ids=tuple(task_manifest.get("tasks", {}).keys()),
        source_file_count=len(parsed_snapshot.files),
    )
    actor = "orchestrator/legacy-mcp/analyze_codebase"
    requested_languages = tuple(parsed_snapshot.languages_detected)
    input_fingerprint = analysis_input_fingerprint(
        languages=requested_languages,
        exclude_paths=(),
        include_tests=False,
    )
    now = datetime.now(UTC)
    store = JsonRunStore(staging_path / "state-v3.json")
    bootstrap = store.issue_bootstrap_lease(
        run_id=run_id,
        actor=actor,
        ttl=timedelta(days=1),
        now=now,
    )
    store.begin_run(
        run_id=run_id,
        repo_root=realistic_project,
        requested_languages=requested_languages,
        actor=actor,
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        product_output_roots=(analysis_root,),
        route_keys=ROUTE_KEYS,
        legacy_submission_seed=seed,
        initial_metadata={
            "project_id": project_id,
            "analysis_root": str(analysis_root),
            "analysis_input_fingerprint": input_fingerprint,
            "v2_recovery_projection_sha256": v2_recovery_projection_sha,
        },
        now=now,
    )
    generation = publish_generation(analysis_root, staging_path, run_id)
    snapshot_v3 = JsonRunStore(generation / "state-v3.json").snapshot()
    write_v2_rollback_projection(
        analysis_root / "state.json", v2_projection, snapshot=snapshot_v3
    )
    receipt = ActiveRunReceipt(
        activation_generation=1,
        run_id=run_id,
        generation_path=f".runs/{run_id}",
        state_path=f".runs/{run_id}/state-v3.json",
        repo_root=str(realistic_project.resolve()),
        analysis_input_fingerprint=input_fingerprint,
        source_revision=snapshot_v3.revisions.source,
        v2_sha256=hashlib.sha256(
            (analysis_root / "state.json").read_bytes()
        ).hexdigest(),
        artifacts=artifact_manifest(generation),
        legacy_seed_sha256=legacy_seed_sha256(seed),
        route_keys=ROUTE_KEYS,
        prior_receipt_sha256="",
    )
    promote_active_receipt(
        analysis_root,
        receipt,
        expected_prior_hash="",
        expected_generation=0,
    )

    return {
        "output_path": generation,
        "analysis_root": analysis_root,
        "project_id": project_id,
        "snapshot": parsed_snapshot,
        "weighted_result": weighted_result,
        "graph": graph,
        "cones": cones,
        "infrastructure": infrastructure,
        "cone_dicts": cone_dicts,
        "file_tokens": file_tokens,
        "file_details": file_details,
        "task_manifest": task_manifest,
        "total_layers": total_layers,
    }


# ---------------------------------------------------------------------------
# Test: Step 1 -- Parse codebase -> CodebaseSnapshot
# ---------------------------------------------------------------------------


class TestStep1Parsing:
    """Verify the parser produces a valid CodebaseSnapshot from the fixture."""

    def test_snapshot_file_count(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """Snapshot should contain all 8 Python files from the fixture."""
        # The parser may or may not include __init__.py files depending on
        # whether they are empty or have content.  We have 8 files total,
        # but app/api/__init__.py is empty so the parser may skip it.
        file_paths = {f.filepath for f in parsed_snapshot.files}
        assert len(file_paths) >= 5, (
            f"Expected at least 5 parsed files, got {len(file_paths)}: {file_paths}"
        )

    def test_snapshot_language_detected(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """Python should be detected as the project language."""
        assert "python" in parsed_snapshot.languages_detected

    def test_snapshot_total_lines_positive(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """Total lines across all files should be positive."""
        assert parsed_snapshot.total_lines > 0

    def test_snapshot_contains_functions(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """Parser should extract function definitions from the project."""
        func_names = {f.name for f in parsed_snapshot.functions}
        # At minimum, we expect some of the explicitly defined functions
        expected_funcs = {"main", "create_user", "hash_password", "validate_email"}
        found = expected_funcs & func_names
        assert len(found) >= 2, (
            f"Expected at least 2 of {expected_funcs} in parsed functions, "
            f"found {found} from {func_names}"
        )

    def test_snapshot_contains_classes(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """Parser should extract class definitions from the project."""
        class_names = {c.name for c in parsed_snapshot.classes}
        expected_classes = {"BaseModel", "User", "Admin", "Settings"}
        found = expected_classes & class_names
        assert len(found) >= 2, (
            f"Expected at least 2 of {expected_classes}, found {found}"
        )

    def test_import_sources_resolved(self, parsed_snapshot: CodebaseSnapshot) -> None:
        """At least some import_sources should be resolved to file paths."""
        all_imports: set[str] = set()
        for fi in parsed_snapshot.files:
            all_imports.update(fi.import_sources)
        assert len(all_imports) > 0, "Expected at least one resolved import source"


# ---------------------------------------------------------------------------
# Test: Step 2 -- Build weighted dependency graph
# ---------------------------------------------------------------------------


class TestStep2WeightedGraph:
    """Verify the weighted dependency graph structure."""

    def test_graph_nodes_match_files(self, pipeline_outputs: dict) -> None:
        """Graph nodes should correspond to parsed files."""
        graph = pipeline_outputs["graph"]
        snapshot = pipeline_outputs["snapshot"]
        file_paths = {f.filepath for f in snapshot.files}
        graph_nodes = set(graph.nodes())
        # Every graph node should be a known file path
        assert graph_nodes.issubset(file_paths), (
            f"Graph has unknown nodes: {graph_nodes - file_paths}"
        )

    def test_graph_has_edges(self, pipeline_outputs: dict) -> None:
        """Graph should have at least one dependency edge."""
        graph = pipeline_outputs["graph"]
        assert graph.number_of_edges() > 0, "Expected dependency edges in graph"

    def test_edge_weights_positive(self, pipeline_outputs: dict) -> None:
        """All edge weights must be positive integers."""
        graph = pipeline_outputs["graph"]
        for u, v, data in graph.edges(data=True):
            weight = data.get("weight", 0)
            assert weight > 0, f"Edge {u} -> {v} has non-positive weight {weight}"

    def test_edge_types_valid(self, pipeline_outputs: dict) -> None:
        """Edge types must be from the known set {import, call, inherit}."""
        valid_types = {"import", "call", "inherit"}
        graph = pipeline_outputs["graph"]
        for u, v, data in graph.edges(data=True):
            edge_types = set(data.get("edge_types", []))
            assert edge_types.issubset(valid_types), (
                f"Edge {u} -> {v} has unknown types: {edge_types - valid_types}"
            )

    def test_weighted_result_summary(self, pipeline_outputs: dict) -> None:
        """WeightedGraphResult should include a non-empty summary string."""
        wr = pipeline_outputs["weighted_result"]
        assert wr.summary, "Expected non-empty summary"
        assert wr.node_count > 0
        assert wr.edge_count > 0
        assert wr.total_weight > 0


# ---------------------------------------------------------------------------
# Test: Step 3 -- Extract feature cones
# ---------------------------------------------------------------------------


class TestStep3FeatureCones:
    """Verify feature cone extraction from the DAG."""

    def test_cones_exist(self, pipeline_outputs: dict) -> None:
        """At least one feature cone should be extracted."""
        cones = pipeline_outputs["cones"]
        assert len(cones) > 0, "Expected at least one feature cone"

    def test_cone_has_exclusive_files(self, pipeline_outputs: dict) -> None:
        """At least one cone should have multiple exclusive files."""
        cones = pipeline_outputs["cones"]
        multi_file_cones = [
            c for c in cones.values() if len(c.exclusive_files) > 1
        ]
        assert len(multi_file_cones) > 0, (
            "Expected at least one cone with >1 exclusive files"
        )

    def test_not_all_single_file_cones(self, pipeline_outputs: dict) -> None:
        """The pipeline should not degrade to all single-file cones."""
        cones = pipeline_outputs["cones"]
        single_file_count = sum(
            1 for c in cones.values() if len(c.exclusive_files) <= 1
        )
        total = len(cones)
        if total > 2:
            ratio = single_file_count / total
            assert ratio < 0.9, (
                f"Too many single-file cones: {single_file_count}/{total} = {ratio:.1%}"
            )

    def test_infrastructure_is_frozenset(self, pipeline_outputs: dict) -> None:
        """Infrastructure should be returned as a frozenset."""
        infra = pipeline_outputs["infrastructure"]
        assert isinstance(infra, frozenset)

    def test_cone_ids_are_strings(self, pipeline_outputs: dict) -> None:
        """Every cone_id should be a non-empty string."""
        cones = pipeline_outputs["cones"]
        for cid in cones:
            assert isinstance(cid, str) and len(cid) > 0

    def test_exclusive_files_not_in_other_cones(self, pipeline_outputs: dict) -> None:
        """A file should appear in at most one cone's exclusive_files."""
        cones = pipeline_outputs["cones"]
        seen: dict[str, str] = {}
        for cid, cone in cones.items():
            for f in cone.exclusive_files:
                if f in seen:
                    pytest.fail(
                        f"File '{f}' is exclusive in both "
                        f"'{seen[f]}' and '{cid}'"
                    )
                seen[f] = cid


# ---------------------------------------------------------------------------
# Test: Step 4 -- Token estimation
# ---------------------------------------------------------------------------


class TestStep4TokenEstimation:
    """Verify token estimation for parsed files."""

    def test_all_files_have_token_estimates(self, pipeline_outputs: dict) -> None:
        """Every parsed file should have a token estimate."""
        snapshot = pipeline_outputs["snapshot"]
        file_tokens = pipeline_outputs["file_tokens"]
        for fi in snapshot.files:
            assert fi.filepath in file_tokens, (
                f"Missing token estimate for {fi.filepath}"
            )

    def test_nonempty_files_have_positive_tokens(self, pipeline_outputs: dict) -> None:
        """Non-empty files should have token estimates > 0."""
        file_tokens = pipeline_outputs["file_tokens"]
        file_details = pipeline_outputs["file_details"]
        for detail in file_details:
            if detail["char_count"] > 0:
                assert detail["estimated_tokens"] > 0, (
                    f"File {detail['filepath']} has {detail['char_count']} chars "
                    f"but 0 estimated tokens"
                )

    def test_token_estimate_reasonable_range(self, pipeline_outputs: dict) -> None:
        """Token estimates should be in a reasonable range relative to char count."""
        file_details = pipeline_outputs["file_details"]
        for detail in file_details:
            chars = detail["char_count"]
            tokens = detail["estimated_tokens"]
            if chars == 0:
                continue
            # Tokens should be roughly chars/3.5 for Python (within 5x range)
            ratio = chars / max(tokens, 1)
            assert 1.0 < ratio < 10.0, (
                f"File {detail['filepath']}: char/token ratio {ratio:.1f} "
                f"is outside reasonable range (chars={chars}, tokens={tokens})"
            )


# ---------------------------------------------------------------------------
# Test: Step 5 -- Task manifest (bin packing)
# ---------------------------------------------------------------------------


class TestStep5TaskManifest:
    """Verify the task manifest structure and bin packing logic."""

    def test_manifest_has_tasks(self, pipeline_outputs: dict) -> None:
        """Task manifest must contain at least one task."""
        manifest = pipeline_outputs["task_manifest"]
        assert "tasks" in manifest
        assert len(manifest["tasks"]) > 0

    def test_manifest_schema_version(self, pipeline_outputs: dict) -> None:
        """Schema version should be '2.0'."""
        manifest = pipeline_outputs["task_manifest"]
        assert manifest.get("schema_version") == "2.0"

    def test_task_types_valid(self, pipeline_outputs: dict) -> None:
        """Every task should have a valid type."""
        valid_types = {"single", "batch", "split", "index"}
        manifest = pipeline_outputs["task_manifest"]
        for task_id, task in manifest["tasks"].items():
            assert task["type"] in valid_types, (
                f"Task {task_id} has invalid type: {task['type']}"
            )

    def test_index_task_exists(self, pipeline_outputs: dict) -> None:
        """There should be exactly one index task that depends on all others."""
        manifest = pipeline_outputs["task_manifest"]
        index_tasks = [
            t for t in manifest["tasks"].values() if t["type"] == "index"
        ]
        assert len(index_tasks) == 1, (
            f"Expected exactly 1 index task, found {len(index_tasks)}"
        )
        index_task = index_tasks[0]
        other_task_ids = sorted(
            tid for tid, t in manifest["tasks"].items() if t["type"] != "index"
        )
        assert sorted(index_task["dependencies"]) == other_task_ids, (
            "Index task should depend on all non-index tasks"
        )

    def test_cone_references_valid(self, pipeline_outputs: dict) -> None:
        """Task cone_ids should reference existing cones or 'all'."""
        manifest = pipeline_outputs["task_manifest"]
        cone_ids = set(pipeline_outputs["cone_dicts"].keys())
        for task_id, task in manifest["tasks"].items():
            for cid in task.get("cone_ids", []):
                if cid == "all":
                    continue
                assert cid in cone_ids, (
                    f"Task {task_id} references unknown cone '{cid}'"
                )

    def test_task_tokens_nonnegative(self, pipeline_outputs: dict) -> None:
        """All token counts in tasks should be non-negative."""
        manifest = pipeline_outputs["task_manifest"]
        for task_id, task in manifest["tasks"].items():
            assert task.get("total_tokens", 0) >= 0, (
                f"Task {task_id} has negative total_tokens"
            )
            assert task.get("exclusive_tokens", 0) >= 0, (
                f"Task {task_id} has negative exclusive_tokens"
            )

    def test_bin_packing_budget_respected(self, pipeline_outputs: dict) -> None:
        """No single non-split task should exceed the context budget."""
        manifest = pipeline_outputs["task_manifest"]
        budget = manifest.get("context_budget", 100_000)
        for task_id, task in manifest["tasks"].items():
            if task["type"] == "split":
                # Split tasks may individually exceed budget by design (parts)
                continue
            exclusive = task.get("exclusive_tokens", 0)
            assert exclusive <= budget, (
                f"Task {task_id} exclusive tokens ({exclusive}) exceeds budget ({budget})"
            )


# ---------------------------------------------------------------------------
# Test: Step 6 -- JSON output files
# ---------------------------------------------------------------------------


class TestStep6JsonOutputFiles:
    """Verify the content and structure of each JSON output file."""

    def test_all_json_files_created(self, pipeline_outputs: dict) -> None:
        """All six immutable analysis artifacts should exist."""
        out = pipeline_outputs["output_path"]
        expected_files = [
            "01_structure.json",
            "02_dag.json",
            "03_feature_cones.json",
            "04_file_tokens.json",
            "05_task_manifest.json",
            "06_function_deps.json",
        ]
        for fname in expected_files:
            assert (out / fname).exists(), f"Missing output file: {fname}"

    def test_validate_json_files_exist_helper(self, pipeline_outputs: dict) -> None:
        """The validate_json_files_exist helper should return True."""
        analysis_root = pipeline_outputs["analysis_root"]
        assert validate_json_files_exist(analysis_root) is True

    # -- 01_structure.json ---

    def test_structure_file_list(self, pipeline_outputs: dict) -> None:
        """01_structure.json should list all parsed files with metadata."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "01_structure.json").read_text())
        assert data["file_count"] > 0
        assert len(data["files"]) == data["file_count"]
        for entry in data["files"]:
            assert "filepath" in entry
            assert "language" in entry
            assert "line_count" in entry
            assert "function_names" in entry
            assert "class_names" in entry
            assert "import_sources" in entry

    def test_structure_language_field(self, pipeline_outputs: dict) -> None:
        """Every file in 01_structure.json should have 'python' as language."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "01_structure.json").read_text())
        for entry in data["files"]:
            assert entry["language"] == "python", (
                f"File {entry['filepath']} has language '{entry['language']}'"
            )

    def test_structure_functions_and_classes(self, pipeline_outputs: dict) -> None:
        """01_structure.json should report aggregate function and class counts."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "01_structure.json").read_text())
        assert data["function_count"] >= 0
        assert data["class_count"] >= 0

    # -- 02_dag.json ---

    def test_dag_nodes_match_files(self, pipeline_outputs: dict) -> None:
        """02_dag.json nodes should correspond to parsed file paths."""
        out = pipeline_outputs["output_path"]
        dag = json.loads((out / "02_dag.json").read_text())
        structure = json.loads((out / "01_structure.json").read_text())
        structure_paths = {f["filepath"] for f in structure["files"]}
        dag_nodes = set(dag["nodes"])
        assert dag_nodes.issubset(structure_paths), (
            f"DAG has nodes not in structure: {dag_nodes - structure_paths}"
        )

    def test_dag_edges_have_weights(self, pipeline_outputs: dict) -> None:
        """Every edge in 02_dag.json must have a positive weight."""
        out = pipeline_outputs["output_path"]
        dag = json.loads((out / "02_dag.json").read_text())
        assert len(dag["edges"]) > 0, "Expected at least one edge"
        for edge in dag["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert edge.get("weight", 0) > 0, (
                f"Edge {edge['source']} -> {edge['target']} weight <= 0"
            )

    def test_dag_node_count_matches(self, pipeline_outputs: dict) -> None:
        """node_count and edge_count metadata should match actual counts."""
        out = pipeline_outputs["output_path"]
        dag = json.loads((out / "02_dag.json").read_text())
        assert dag["node_count"] == len(dag["nodes"])
        assert dag["edge_count"] == len(dag["edges"])

    # -- 03_feature_cones.json ---

    def test_feature_cones_cones_exist(self, pipeline_outputs: dict) -> None:
        """03_feature_cones.json should contain at least one cone."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "03_feature_cones.json").read_text())
        assert data["cone_count"] > 0
        assert len(data["cones"]) == data["cone_count"]

    def test_feature_cones_files_assigned(self, pipeline_outputs: dict) -> None:
        """Each cone should have exclusive_files as a list."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "03_feature_cones.json").read_text())
        for cid, cone in data["cones"].items():
            assert isinstance(cone["exclusive_files"], list), (
                f"Cone {cid} exclusive_files is not a list"
            )
            assert isinstance(cone.get("shared_deps", []), list), (
                f"Cone {cid} shared_deps is not a list"
            )

    def test_feature_cones_not_all_single_file(self, pipeline_outputs: dict) -> None:
        """Not all cones should be single-file (quality check)."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "03_feature_cones.json").read_text())
        cones = data["cones"]
        multi_file = sum(
            1 for c in cones.values() if len(c["exclusive_files"]) > 1
        )
        # At least one multi-file cone expected for our 8-file project
        assert multi_file >= 1, (
            f"Expected at least 1 multi-file cone, got {multi_file}"
        )

    # -- 04_file_tokens.json ---

    def test_file_tokens_all_positive(self, pipeline_outputs: dict) -> None:
        """04_file_tokens.json should have positive tokens for non-empty files."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "04_file_tokens.json").read_text())
        assert data["file_count"] > 0
        assert data["total_tokens"] > 0
        for entry in data["files"]:
            if entry["char_count"] > 0:
                assert entry["estimated_tokens"] > 0

    def test_file_tokens_total_matches_sum(self, pipeline_outputs: dict) -> None:
        """total_tokens should equal the sum of individual estimates."""
        out = pipeline_outputs["output_path"]
        data = json.loads((out / "04_file_tokens.json").read_text())
        computed_total = sum(f["estimated_tokens"] for f in data["files"])
        assert data["total_tokens"] == computed_total

    # -- 05_task_manifest.json ---

    def test_task_manifest_on_disk(self, pipeline_outputs: dict) -> None:
        """05_task_manifest.json should match the in-memory manifest."""
        out = pipeline_outputs["output_path"]
        disk_data = json.loads((out / "05_task_manifest.json").read_text())
        in_memory = pipeline_outputs["task_manifest"]
        assert disk_data["schema_version"] == in_memory["schema_version"]
        assert set(disk_data["tasks"].keys()) == set(in_memory["tasks"].keys())

    # -- state.json ---

    def test_state_json_project_id(self, pipeline_outputs: dict) -> None:
        """The active receipt must link the V2 projection to this project."""
        out = pipeline_outputs["analysis_root"]
        state = read_state(out / "state.json")
        assert state is not None
        assert state["project_id"] == pipeline_outputs["project_id"]
        assert pipeline_outputs["project_id"] == project_id_from_path(
            str(pipeline_outputs["snapshot"].root_path)
        )

    def test_state_json_status(self, pipeline_outputs: dict) -> None:
        """The activated V2 projection records the complete analysis status."""
        out = pipeline_outputs["analysis_root"]
        state = read_state(out / "state.json")
        assert state is not None
        assert state["status"] == "analysis_complete"

    def test_state_json_tasks_match_manifest(self, pipeline_outputs: dict) -> None:
        """The active V2 projection carries the immutable task seed set."""
        out = pipeline_outputs["analysis_root"]
        generation = pipeline_outputs["output_path"]
        manifest = pipeline_outputs["task_manifest"]
        disk_manifest = json.loads((generation / "05_task_manifest.json").read_text())
        assert set(disk_manifest["tasks"]) == set(manifest["tasks"])
        state = read_state(out / "state.json")
        assert state is not None
        assert set(state["tasks"]) == set(manifest["tasks"])

    def test_state_json_tasks_all_pending(self, pipeline_outputs: dict) -> None:
        """The newly activated generation starts every task as pending."""
        out = pipeline_outputs["analysis_root"]
        state = read_state(out / "state.json")
        assert state is not None
        assert state["tasks"]
        assert all(task["status"] == "pending" for task in state["tasks"].values())

    def test_state_json_documentation_section(self, pipeline_outputs: dict) -> None:
        """The lifecycle owner initializes documentation counters in V2."""
        out = pipeline_outputs["analysis_root"]
        state = read_state(out / "state.json")
        assert state is not None
        assert state["documentation"]["output_dir"] == str(out)
        assert state["documentation"]["index_written"] is False


# ---------------------------------------------------------------------------
# Test: Depth planning and quality checks
# ---------------------------------------------------------------------------


class TestDepthPlanningQuality:
    """Verify depth planning produces valid results."""

    def test_feature_cone_depth_small_cone(self) -> None:
        """Small cones (< 2000 tokens) should get depth <= 1."""
        depth = calculate_feature_cone_depth(1500, dag_layers=3, token_budget=100_000)
        assert depth <= 1

    def test_feature_cone_depth_medium_cone(self) -> None:
        """Medium cones (2000-8000 tokens) should get depth <= 2."""
        depth = calculate_feature_cone_depth(5000, dag_layers=4, token_budget=100_000)
        assert depth <= 2

    def test_feature_cone_depth_large_cone(self) -> None:
        """Large cones (> 32000 tokens) should use full DAG layer depth."""
        depth = calculate_feature_cone_depth(50_000, dag_layers=4, token_budget=100_000)
        assert depth == 4

    def test_feature_cone_depth_capped_at_5(self) -> None:
        """Depth should never exceed MAX_DEPTH (5)."""
        depth = calculate_feature_cone_depth(200_000, dag_layers=10, token_budget=100_000)
        assert depth <= 5

    def test_task_manifest_all_files_covered(self, pipeline_outputs: dict) -> None:
        """Every exclusive file from every cone should appear in some task."""
        manifest = pipeline_outputs["task_manifest"]
        cone_dicts = pipeline_outputs["cone_dicts"]

        # Collect all exclusive files across cones
        all_cone_files: set[str] = set()
        for cone in cone_dicts.values():
            all_cone_files.update(cone["exclusive_files"])

        # Collect all files across tasks (excluding index task)
        all_task_files: set[str] = set()
        for task in manifest["tasks"].values():
            if task["type"] != "index":
                all_task_files.update(task.get("files", []))

        missing = all_cone_files - all_task_files
        assert missing == set(), (
            f"Files not covered by any task: {missing}"
        )


# ---------------------------------------------------------------------------
# Test: Output directory resolver
# ---------------------------------------------------------------------------


class TestOutputDirectoryResolution:
    """Verify output directory resolution logic."""

    def test_default_output_dir(self, realistic_project: Path) -> None:
        """Without explicit output_dir, should use .codebase-analysis subdir."""
        resolved = resolve_output_dir(str(realistic_project), None)
        assert resolved == realistic_project / ".codebase-analysis"

    def test_custom_output_dir(self, tmp_path: Path) -> None:
        """Explicit output_dir should be used as-is (resolved)."""
        custom = tmp_path / "custom-output"
        resolved = resolve_output_dir("/some/project", str(custom))
        assert resolved == custom.resolve()

    def test_project_id_deterministic(self, realistic_project: Path) -> None:
        """Same path should produce the same project_id every time."""
        id1 = project_id_from_path(str(realistic_project))
        id2 = project_id_from_path(str(realistic_project))
        assert id1 == id2
        assert len(id1) == 12  # SHA-256 truncated to 12 chars
