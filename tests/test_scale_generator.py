"""Contract tests for the deterministic T5 scale-corpus generator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.generate_scale_corpus import CorpusParameters, generate_corpus


def _manifest_and_tree(root: Path) -> tuple[bytes, str]:
    manifest = (root / "corpus_manifest.json").read_bytes()
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "corpus_manifest.json"
    )
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return manifest, digest.hexdigest()


def _small_parameters() -> CorpusParameters:
    return CorpusParameters(
        requested_symbols=12,
        file_count=3,
        symbols_per_file=4,
        package_count=1,
        fan_in=1,
    )


def test_same_inputs_are_byte_identical_across_independent_output_dirs(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    params = _small_parameters()

    generate_corpus(first, seed=17, parameters=params)
    generate_corpus(second, seed=17, parameters=params)

    first_manifest, first_tree = _manifest_and_tree(first)
    second_manifest, second_tree = _manifest_and_tree(second)
    assert first_manifest == second_manifest
    assert first_tree == second_tree
    payload = json.loads(first_manifest)
    assert payload["requested_symbol_denominator"] == 12
    assert payload["observed_symbol_denominator"] == 12


def test_seed_change_changes_tree_hash(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    params = _small_parameters()

    generate_corpus(first, seed=17, parameters=params)
    generate_corpus(second, seed=18, parameters=params)

    assert _manifest_and_tree(first)[1] != _manifest_and_tree(second)[1]


@pytest.mark.parametrize(
    "parameters",
    [
        CorpusParameters(requested_symbols=0, file_count=1, symbols_per_file=1, package_count=1),
        CorpusParameters(requested_symbols=3, file_count=2, symbols_per_file=2, package_count=1),
        CorpusParameters(requested_symbols=4, file_count=2, symbols_per_file=2, package_count=3),
        CorpusParameters(requested_symbols=4, file_count=2, symbols_per_file=2, package_count=1, fan_in=2),
    ],
)
def test_invalid_sizes_fail_closed(tmp_path: Path, parameters: CorpusParameters) -> None:
    with pytest.raises(ValueError):
        generate_corpus(tmp_path / "out", seed=1, parameters=parameters)


def test_malformed_and_unsafe_paths_fail_closed(tmp_path: Path) -> None:
    params = _small_parameters()
    with pytest.raises(ValueError, match="absolute"):
        generate_corpus(Path("relative-output"), seed=1, parameters=params)

    existing_file = tmp_path / "not-a-directory"
    existing_file.write_text("sentinel", encoding="utf-8")
    with pytest.raises(ValueError, match="directory"):
        generate_corpus(existing_file, seed=1, parameters=params)

    non_empty = tmp_path / "non-empty"
    non_empty.mkdir()
    (non_empty / "sentinel").write_text("sentinel", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        generate_corpus(non_empty, seed=1, parameters=params)

    unsafe = tmp_path / "unsafe"
    unsafe.mkdir()
    link = tmp_path / "symlink"
    link.symlink_to(unsafe, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        generate_corpus(link, seed=1, parameters=params)

