"""Contract tests for the independent filesystem source denominator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ir.models import SourceUnitState
from src.parser.backend import (
    BackendHealth,
    BackendStatus,
    FailureCode,
    PythonAstBackend,
    SyntaxArtifact,
    TypedFailure,
)
from src.state.universe import (
    SourceOutcome,
    build_source_universe,
    classify_source,
    enumerate_source_universe,
)


def _health(status: BackendStatus = BackendStatus.HEALTHY) -> BackendHealth:
    return BackendHealth(
        backend_id="python_ast",
        backend_version="3.13",
        status=status,
        supported_languages=("python",),
        semantic_tier="heuristic",
        toolchain_conditions=("python=3.13",),
        limitations=() if status is BackendStatus.HEALTHY else ("probe failed",),
    )


def test_enumeration_uses_filesystem_denominator_and_canonical_paths(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("docs\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("x = 2\n", encoding="utf-8")

    result = enumerate_source_universe(
        tmp_path,
        requested_languages=("python",),
        exclude_globs=("ignored.py",),
    )

    assert tuple(source.path for source in result.sources) == (
        "README.md",
        "ignored.py",
        "pkg/a.py",
    )
    assert result.denominator == 3
    assert result.sources[1].state is SourceUnitState.EXCLUDED
    assert result.sources[2].content_hash is not None


def test_source_revision_changes_when_source_bytes_change(tmp_path: Path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    before = enumerate_source_universe(tmp_path, requested_languages=("python",))
    source.write_text("x = 2\n", encoding="utf-8")
    after = enumerate_source_universe(tmp_path, requested_languages=("python",))
    assert before.source_revision != after.source_revision


def test_exact_five_way_conservation(tmp_path: Path):
    for name, content in {
        "ok.py": "x = 1\n",
        "bad.py": "def broken(:\n",
        "offline.py": "x = 2\n",
        "notes.md": "notes\n",
        "skip.py": "x = 3\n",
    }.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    enumeration = enumerate_source_universe(
        tmp_path,
        requested_languages=("python",),
        exclude_globs=("skip.py",),
    )
    by_path = {source.path: source for source in enumeration.sources}
    ok_unit = by_path["ok.py"].to_source_unit(enumeration.source_revision)
    ok_artifact = PythonAstBackend(root=tmp_path).parse(ok_unit)
    assert isinstance(ok_artifact, SyntaxArtifact)
    outcomes = {
        "ok.py": SourceOutcome.syntax(ok_artifact),
        "bad.py": SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message="syntax",
                backend_id="python_ast",
                language="python",
            ),
            health=_health(),
        ),
        "offline.py": SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.BACKEND_UNAVAILABLE,
                message="offline",
                backend_id="python_ast",
                language="python",
            ),
            health=_health(BackendStatus.UNAVAILABLE),
        ),
    }

    universe = build_source_universe(enumeration, outcomes)

    assert set(universe.partition) == {
        SourceUnitState.INDEXED,
        SourceUnitState.PARSE_ERROR,
        SourceUnitState.UNSUPPORTED,
        SourceUnitState.UNAVAILABLE,
        SourceUnitState.EXCLUDED,
    }
    assert sum(map(len, universe.partition.values())) == len(by_path) == 5
    assert universe.partition[SourceUnitState.INDEXED] == ("ok.py",)
    assert universe.partition[SourceUnitState.UNSUPPORTED] == ("notes.md",)
    assert universe.partition[SourceUnitState.EXCLUDED] == ("skip.py",)


def test_missing_supported_outcome_fails_closed(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    enumeration = enumerate_source_universe(tmp_path, requested_languages=("python",))
    with pytest.raises(ValueError, match="missing terminal outcomes"):
        build_source_universe(enumeration, {})


def test_unknown_or_duplicate_alias_outcomes_fail_closed(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    enumeration = enumerate_source_universe(tmp_path, requested_languages=("python",))
    unit = enumeration.sources[0].to_source_unit(enumeration.source_revision)
    artifact = PythonAstBackend(root=tmp_path).parse(unit)
    assert isinstance(artifact, SyntaxArtifact)
    indexed = SourceOutcome.syntax(artifact)
    with pytest.raises(ValueError, match="unknown source paths"):
        build_source_universe(enumeration, {"a.py": indexed, "missing.py": indexed})
    with pytest.raises(ValueError, match="canonical"):
        build_source_universe(enumeration, {"pkg/../a.py": indexed})


@pytest.mark.parametrize(
    "code,status",
    [
        (FailureCode.BACKEND_UNAVAILABLE, BackendStatus.UNAVAILABLE),
        (FailureCode.INCOMPATIBLE_API, BackendStatus.INCOMPATIBLE),
        (FailureCode.BACKEND_ERROR, BackendStatus.ERROR),
    ],
)
def test_unavailable_requires_typed_failure_and_matching_health_provenance(
    tmp_path: Path, code: FailureCode, status: BackendStatus
):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    source = enumerate_source_universe(
        tmp_path, requested_languages=("python",)
    ).sources[0]
    record = classify_source(
        source,
        SourceOutcome.failure(
            TypedFailure(
                code=code,
                message="backend boundary failed",
                backend_id="python_ast",
                language="python",
                details=("receipt=probe-1",),
            ),
            health=_health(status),
        ),
    )
    assert record.state is SourceUnitState.UNAVAILABLE
    assert record.provenance.failure_code == code.value
    assert record.provenance.backend_version == "3.13"
    assert record.provenance.toolchain_conditions == ("python=3.13",)
    assert record.provenance.evidence == ("receipt=probe-1",)


def test_extension_capability_or_worker_assertion_cannot_assign_unavailable(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    source = enumerate_source_universe(
        tmp_path, requested_languages=("python",)
    ).sources[0]
    with pytest.raises(TypeError, match="SourceOutcome"):
        classify_source(source, "unavailable")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exactly one"):
        classify_source(
            source,
            SourceOutcome(
                backend_id="worker-claimed", backend_version="1", evidence=("asserted",)
            ),
        )
    with pytest.raises(ValueError, match="health provenance"):
        classify_source(
            source,
            SourceOutcome.failure(
                TypedFailure(
                    code=FailureCode.BACKEND_UNAVAILABLE,
                    message="claimed",
                    backend_id="python_ast",
                    language="python",
                ),
                health=None,
            ),
        )


def test_unsupported_and_parse_error_remain_distinct(tmp_path: Path):
    (tmp_path / "a.py").write_text("bad", encoding="utf-8")
    source = enumerate_source_universe(
        tmp_path, requested_languages=("python",)
    ).sources[0]
    unsupported = classify_source(
        source,
        SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.UNSUPPORTED_LANGUAGE,
                message="unsupported",
                backend_id="python_ast",
                language="python",
            ),
            health=_health(),
        ),
    )
    parse_error = classify_source(
        source,
        SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message="syntax",
                backend_id="python_ast",
                language="python",
            ),
            health=_health(),
        ),
    )
    assert unsupported.state is SourceUnitState.UNSUPPORTED
    assert parse_error.state is SourceUnitState.PARSE_ERROR


def test_real_syntax_artifact_is_an_indexed_typed_outcome(tmp_path: Path):
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    enumeration = enumerate_source_universe(tmp_path, requested_languages=("python",))
    unit = enumeration.sources[0].to_source_unit(enumeration.source_revision)
    artifact = PythonAstBackend(root=tmp_path).parse(unit)
    assert isinstance(artifact, SyntaxArtifact)
    record = classify_source(enumeration.sources[0], SourceOutcome.syntax(artifact))
    assert record.state is SourceUnitState.INDEXED


def test_builtin_non_source_roots_are_pruned_before_any_byte_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    hidden = (
        tmp_path / ".git" / "objects" / "object",
        tmp_path / ".venv" / "lib" / "dependency.py",
        tmp_path / "node_modules" / "pkg" / "index.js",
        tmp_path / "pkg" / "__pycache__" / "a.pyc",
    )
    for path in hidden:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"opaque")
    original = Path.read_bytes
    reads: list[str] = []

    def guarded_read(path: Path) -> bytes:
        relative = path.relative_to(tmp_path).as_posix()
        reads.append(relative)
        if any(relative == item.relative_to(tmp_path).as_posix() for item in hidden):
            raise AssertionError(f"non-source root was byte-read: {relative}")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    before = enumerate_source_universe(tmp_path, requested_languages=("python",))
    for path in hidden:
        path.write_bytes(b"changed")
    after = enumerate_source_universe(tmp_path, requested_languages=("python",))

    assert tuple(source.path for source in before.sources) == ("a.py",)
    assert after.source_revision == before.source_revision
    assert reads == ["a.py", "a.py"]


def test_nested_non_source_basenames_are_pruned_but_same_prefixes_remain_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    hidden: list[Path] = []
    for index, dirname in enumerate(
        (".git", ".venv", "venv", "node_modules", "__pycache__")
    ):
        path = tmp_path / "packages" / f"pkg-{index}" / dirname / "hidden.py"
        path.parent.mkdir(parents=True)
        path.write_text(f"hidden = {index}\n", encoding="utf-8")
        hidden.append(path)
    visible: list[Path] = []
    for index, dirname in enumerate(
        (".git-tools", ".venv-src", "venv_tools", "node_modules_app", "__pycache__tools")
    ):
        path = tmp_path / "packages" / f"visible-{index}" / dirname / "kept.py"
        path.parent.mkdir(parents=True)
        path.write_text(f"kept = {index}\n", encoding="utf-8")
        visible.append(path)
    original = Path.read_bytes
    reads: list[str] = []

    def guarded_read(path: Path) -> bytes:
        relative = path.relative_to(tmp_path).as_posix()
        reads.append(relative)
        if path in hidden:
            raise AssertionError(f"nested non-source root was byte-read: {relative}")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    before = enumerate_source_universe(tmp_path, requested_languages=("python",))
    for path in hidden:
        path.write_text("mutated = True\n", encoding="utf-8")
    after = enumerate_source_universe(
        tmp_path,
        requested_languages=(),
        frozen_policy=before.policy_serialization,
    )

    expected = tuple(sorted(["a.py", *(path.relative_to(tmp_path).as_posix() for path in visible)]))
    assert tuple(item.path for item in before.sources) == expected
    assert tuple(item.path for item in after.sources) == expected
    assert before.source_revision == after.source_revision
    assert all(path.relative_to(tmp_path).as_posix() not in reads for path in hidden)
    policy = json.loads(before.policy_serialization)
    assert policy["built_in_roots"] == sorted(
        (
            ".codebase-analysis",
            ".codebase-docs",
            "**/.git",
            "**/.venv",
            "**/venv",
            "**/node_modules",
            "**/__pycache__",
        )
    )


def test_user_exclusion_is_terminal_without_byte_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    secret = tmp_path / "secret.py"
    secret.write_text("secret\n", encoding="utf-8")
    original = Path.read_bytes

    def guarded_read(path: Path) -> bytes:
        if path == secret:
            raise AssertionError("excluded source was byte-read")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    result = enumerate_source_universe(
        tmp_path, requested_languages=("python",), exclude_globs=("secret.py",)
    )

    excluded = [source for source in result.sources if source.path == "secret.py"]
    assert len(excluded) == 1
    assert excluded[0].state is SourceUnitState.EXCLUDED
    assert excluded[0].content_hash is None


def test_source_outcome_requires_exactly_one_payload_and_no_redundant_provenance(
    tmp_path: Path,
):
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    enumeration = enumerate_source_universe(tmp_path, requested_languages=("python",))
    source = enumeration.sources[0]
    artifact = PythonAstBackend(root=tmp_path).parse(
        source.to_source_unit(enumeration.source_revision)
    )
    failure = TypedFailure(
        code=FailureCode.PARSE_ERROR,
        message="syntax",
        backend_id="python_ast",
        language="python",
    )
    assert isinstance(artifact, SyntaxArtifact)

    with pytest.raises(ValueError, match="exactly one"):
        SourceOutcome()
    with pytest.raises(ValueError, match="exactly one"):
        SourceOutcome(artifact=artifact, typed_failure=failure)
    with pytest.raises(ValueError, match="artifact.*health"):
        SourceOutcome(artifact=artifact, health=_health())
    with pytest.raises(ValueError, match="redundant provenance"):
        SourceOutcome(typed_failure=failure, backend_id="python_ast")

    contradictory = SourceOutcome.syntax(artifact)
    object.__setattr__(contradictory, "typed_failure", failure)
    with pytest.raises(ValueError, match="exactly one"):
        classify_source(source, contradictory)


@pytest.mark.parametrize(
    "code,health,error",
    [
        (FailureCode.BACKEND_UNAVAILABLE, None, "requires health"),
        (FailureCode.BACKEND_UNAVAILABLE, _health(BackendStatus.ERROR), "status"),
        (
            FailureCode.BACKEND_UNAVAILABLE,
            BackendHealth(
                backend_id="other",
                backend_version="1",
                status=BackendStatus.UNAVAILABLE,
                supported_languages=("python",),
                semantic_tier="heuristic",
                toolchain_conditions=(),
                limitations=("offline",),
            ),
            "backend",
        ),
        (FailureCode.PARSE_ERROR, _health(BackendStatus.ERROR), "healthy"),
        (FailureCode.UNSUPPORTED_LANGUAGE, _health(BackendStatus.UNAVAILABLE), "healthy"),
    ],
)
def test_source_outcome_rejects_inconsistent_failure_health(
    code: FailureCode, health: BackendHealth | None, error: str
):
    failure = TypedFailure(
        code=code,
        message="failed",
        backend_id="python_ast",
        language="python",
    )
    with pytest.raises(ValueError, match=error):
        SourceOutcome.failure(failure, health=health)


@pytest.mark.parametrize("code", [FailureCode.PARSE_ERROR, FailureCode.UNSUPPORTED_LANGUAGE])
@pytest.mark.parametrize("health", [None, _health()])
def test_parse_and_unsupported_accept_absent_or_matching_healthy_health(
    code: FailureCode, health: BackendHealth | None
):
    outcome = SourceOutcome.failure(
        TypedFailure(
            code=code,
            message="terminal",
            backend_id="python_ast",
            language="python",
        ),
        health=health,
    )
    assert outcome.typed_failure is not None


@pytest.mark.parametrize("configured", [".", "../repo/generated"])
def test_ambiguous_or_repo_wide_product_root_fails_closed(
    tmp_path: Path, configured: str
):
    with pytest.raises(ValueError, match="product root"):
        enumerate_source_universe(
            tmp_path,
            requested_languages=("python",),
            product_output_roots=(configured,),
        )
