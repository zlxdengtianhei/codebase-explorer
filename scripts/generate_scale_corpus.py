"""Generate a deterministic Python source corpus for the T5 scale gate.

The generator deliberately has no repository-specific input.  A corpus is
identified by its version, integer seed, and the complete ``CorpusParameters``
record.  Source files contain only relative names and deterministic values, so
the same inputs produce the same bytes in any independent output directory.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


GENERATOR_VERSION = "cbe-scale-corpus/1"
MANIFEST_FILENAME = "corpus_manifest.json"
TOLERANCE_PERCENT = 1.0


@dataclass(frozen=True)
class CorpusParameters:
    """All load-bearing corpus-shape inputs, persisted in the manifest."""

    requested_symbols: int = 50_000
    file_count: int = 250
    symbols_per_file: int = 200
    package_count: int = 10
    fan_in: int = 1

    def validate(self) -> None:
        fields = {
            "requested_symbols": self.requested_symbols,
            "file_count": self.file_count,
            "symbols_per_file": self.symbols_per_file,
            "package_count": self.package_count,
            "fan_in": self.fan_in,
        }
        for name, value in fields.items():
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
        if self.requested_symbols <= 0:
            raise ValueError("requested_symbols must be positive")
        if self.file_count <= 0:
            raise ValueError("file_count must be positive")
        if self.symbols_per_file <= 0:
            raise ValueError("symbols_per_file must be positive")
        if self.package_count <= 0 or self.package_count > self.file_count:
            raise ValueError("package_count must be in [1, file_count]")
        if self.fan_in < 0 or self.fan_in >= self.symbols_per_file:
            raise ValueError("fan_in must be in [0, symbols_per_file)")
        observed = self.file_count * self.symbols_per_file
        if observed != self.requested_symbols:
            raise ValueError(
                "requested_symbols must equal file_count * symbols_per_file "
                f"({self.requested_symbols} != {observed})"
            )


@dataclass(frozen=True)
class GenerationResult:
    """Stable generation readings returned to callers and evidence scripts."""

    output_dir: str
    generator_version: str
    seed: int
    parameters: CorpusParameters
    requested_symbol_denominator: int
    observed_symbol_denominator: int
    tolerance_percent: float
    manifest_path: str
    source_manifest_sha256: str
    tree_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_dir": self.output_dir,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "parameters": asdict(self.parameters),
            "requested_symbol_denominator": self.requested_symbol_denominator,
            "observed_symbol_denominator": self.observed_symbol_denominator,
            "tolerance_percent": self.tolerance_percent,
            "manifest_path": self.manifest_path,
            "source_manifest_sha256": self.source_manifest_sha256,
            "tree_sha256": self.tree_sha256,
        }


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_seed(seed: int) -> None:
    if type(seed) is not int:
        raise ValueError("seed must be an integer")


def _validate_output_dir(output_dir: str | os.PathLike[str]) -> Path:
    try:
        raw = os.fspath(output_dir)
    except TypeError as exc:
        raise ValueError("output directory must be a filesystem path") from exc
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ValueError("output directory must be absolute")
    if path == Path(path.anchor) or ".." in path.parts:
        raise ValueError("output directory path is unsafe")
    if path.is_symlink():
        raise ValueError("output directory must not be a symlink")

    # Reject symlinked or non-directory ancestors before creating anything.
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            # A system temporary root such as macOS ``/tmp`` may itself be a
            # symlink.  It is safe to traverse an existing directory ancestor;
            # the output target is still rejected below when it is a symlink.
            if not current.resolve().is_dir():
                raise ValueError("output directory path contains an unsafe symlink")
            continue
        if current.exists() and not current.is_dir():
            raise ValueError("output directory path contains a non-directory")

    if path.exists():
        if not path.is_dir():
            raise ValueError("output directory must be a directory")
        if any(path.iterdir()):
            raise ValueError("output directory must be empty")
    elif os.path.lexists(path):
        raise ValueError("output directory is a dangling symlink")
    return path


def _module_name(file_index: int, local_index: int) -> str:
    return f"symbol_{file_index:04d}_{local_index:04d}"


def _module_source(
    *,
    file_index: int,
    package_index: int,
    symbols_per_file: int,
    fan_in: int,
    seed_digest: str,
    rng: random.Random,
) -> str:
    lines = [
        '"""Deterministic T5 scale fixture module."""',
        f"# generator={GENERATOR_VERSION} package={package_index:03d} file={file_index:04d}",
        "",
    ]
    for local_index in range(symbols_per_file):
        name = _module_name(file_index, local_index)
        lines.extend(
            [
                f"def {name}() -> object:",
                f'    """Generated symbol {name}; seed={seed_digest}."""',
            ]
        )
        target_count = min(fan_in, local_index)
        targets = sorted(rng.sample(range(local_index), target_count))
        if not targets:
            expression = repr((file_index << 16) + local_index)
        elif len(targets) == 1:
            expression = f"{_module_name(file_index, targets[0])}()"
        else:
            expression = "(" + ", ".join(
                f"{_module_name(file_index, target)}()" for target in targets
            ) + ")"
        lines.extend([f"    return {expression}", ""])
    return "\n".join(lines).rstrip() + "\n"


def _package_source(package_index: int, seed_digest: str) -> str:
    return (
        '"""Deterministic package marker for the T5 scale fixture."""\n'
        f"# generator={GENERATOR_VERSION} package={package_index:03d} seed={seed_digest}\n"
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _iter_files(root: Path, *, exclude: Iterable[str] = ()) -> tuple[Path, ...]:
    excluded = frozenset(exclude)
    return tuple(
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    )


def tree_sha256(root: str | Path, *, exclude: Sequence[str] = ()) -> str:
    """Hash sorted relative paths and bytes, independent of filesystem roots."""

    base = Path(root).resolve()
    digest = hashlib.sha256()
    for path in _iter_files(base, exclude=exclude):
        relative = path.relative_to(base).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _source_manifest(root: Path) -> tuple[list[dict[str, str]], str]:
    rows: list[dict[str, str]] = []
    for path in _iter_files(root, exclude=(MANIFEST_FILENAME,)):
        relative = path.relative_to(root).as_posix()
        rows.append({"path": relative, "sha256": _sha256(path.read_bytes())})
    return rows, _sha256(_canonical_json(rows))


def count_python_symbols(root: str | Path) -> int:
    """Count the accepted AST symbol denominator independently of generation."""

    total = 0
    base = Path(root).resolve()
    for path in sorted(base.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        total += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in ast.walk(tree)
        )
    return total


def generate_corpus(
    output_dir: str | os.PathLike[str],
    *,
    seed: int,
    parameters: CorpusParameters | None = None,
) -> GenerationResult:
    """Generate one real source corpus and its deterministic manifest."""

    _validate_seed(seed)
    params = parameters or CorpusParameters()
    params.validate()
    root = _validate_output_dir(output_dir)
    root.mkdir(parents=True, exist_ok=False)

    seed_digest = _sha256(str(seed).encode("ascii"))[:16]
    rng = random.Random(seed)
    for file_index in range(params.file_count):
        package_index = file_index % params.package_count
        package = root / f"package_{package_index:03d}"
        if not (package / "__init__.py").exists():
            _write_text(package / "__init__.py", _package_source(package_index, seed_digest))
        _write_text(
            package / f"module_{file_index:04d}.py",
            _module_source(
                file_index=file_index,
                package_index=package_index,
                symbols_per_file=params.symbols_per_file,
                fan_in=params.fan_in,
                seed_digest=seed_digest,
                rng=rng,
            ),
        )

    observed = count_python_symbols(root)
    source_files, source_manifest_hash = _source_manifest(root)
    tree_hash = tree_sha256(root, exclude=(MANIFEST_FILENAME,))
    manifest = {
        "schema": "cbe-scale-corpus-manifest/1",
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "parameters": asdict(params),
        "requested_symbol_denominator": params.requested_symbols,
        "observed_symbol_denominator": observed,
        "tolerance_percent": TOLERANCE_PERCENT,
        "source_manifest_sha256": source_manifest_hash,
        "tree_sha256": tree_hash,
        "tree_hash_excludes": [MANIFEST_FILENAME],
        "source_files": source_files,
    }
    manifest_path = root / MANIFEST_FILENAME
    manifest_path.write_bytes(_canonical_json(manifest))
    return GenerationResult(
        output_dir=root.as_posix(),
        generator_version=GENERATOR_VERSION,
        seed=seed,
        parameters=params,
        requested_symbol_denominator=params.requested_symbols,
        observed_symbol_denominator=observed,
        tolerance_percent=TOLERANCE_PERCENT,
        manifest_path=manifest_path.as_posix(),
        source_manifest_sha256=source_manifest_hash,
        tree_sha256=tree_hash,
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Absolute empty output directory")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--requested-symbols", type=int, default=50_000)
    parser.add_argument("--file-count", type=int, default=250)
    parser.add_argument("--symbols-per-file", type=int, default=200)
    parser.add_argument("--package-count", type=int, default=10)
    parser.add_argument("--fan-in", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    result = generate_corpus(
        args.output,
        seed=args.seed,
        parameters=CorpusParameters(
            requested_symbols=args.requested_symbols,
            file_count=args.file_count,
            symbols_per_file=args.symbols_per_file,
            package_count=args.package_count,
            fan_in=args.fan_in,
        ),
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
