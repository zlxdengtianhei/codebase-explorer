"""Packing output/order pin recorded with dd82d6c, plus an import-work bound."""
import random

import pytest

from cbe import batching


@pytest.mark.parametrize("strict", [False, True])
def test_indexed_directory_matches_preindex_order_and_reads_imports_once(strict):
    class CountedImports(set):
        def __init__(self, values):
            super().__init__(values)
            self.reads = 0

        def __iter__(self):
            self.reads += 1
            return super().__iter__()

    rng = random.Random(731)
    files = []
    for i in range(48):
        imports = {f"prefix.pkg.area.f{rng.randrange(48):02}" for _ in range(4)}
        imports.update({f"f{(i + 3) % 48:02}.py", f"./f{(i + 1) % 48:02}"})
        files.append(batching.SourceFile(f"pkg/area/f{i:02}.py", "", rng.randrange(400, 2400), "", [],
                                         CountedImports(imports)))
    # File order within each group is also part of the old contract. Normal
    # fill reorders these three groups by size; strict packing preserves order.
    expected = [
        [0, 4, 1, 46, 27, 43, 14, 18, 17, 34, 41, 35, 9, 6, 24, 21, 32],
        [2, 3, 12, 15, 28, 31, 37, 40, 45, 25, 22, 42],
        [5, 11, 44, 29, 13, 47, 26, 16, 20, 23, 30, 10, 8, 19, 7, 39, 36, 33, 38],
    ]
    if not strict:
        expected = [expected[2], expected[0], expected[1]]
    packed = batching._pack_directory(list(reversed(files)), strict=strict)
    assert [[item.path for item in group] for group in packed] == [
        [f"pkg/area/f{i:02}.py" for i in group] for group in expected]
    # More merging may not cause repeated import/candidate scans.
    assert all(item.imports.reads == 1 for item in files)


def test_index_preserves_boolean_matches_for_multiple_aliases_and_empty_imports():
    files = [batching.SourceFile("a.py", "", 10_000, "", [], {"b", "b.py", "prefix.b", ""}),
             batching.SourceFile("b.py", "", 10_000, "", [], set()),
             batching.SourceFile("c.py", "", 10_000, "", [], {"a"})]
    # a -> b counts once despite three matching aliases; the empty import
    # matches the empty top-level candidate, as the original exact test did.
    packed = batching._pack_directory(files, strict=True)
    assert [[item.path for item in group] for group in packed] == [["a.py", "c.py"], ["b.py"]]


def test_equal_import_weights_and_token_distances_keep_preindex_pair_order():
    files = [batching.SourceFile("pkg/a.py", "", 10_000, "", [], {"b", "c"}),
             batching.SourceFile("pkg/b.py", "", 10_000, "", [], set()),
             batching.SourceFile("pkg/c.py", "", 10_000, "", [], set())]
    # a-b and a-c each have one import and exactly meet the 20k target.
    # Only one pair fits: merging all three would exceed the 25k cap.
    # Fixed expectation independently recorded with dd82d6c's plan(), loaded
    # via git show; do not derive it from the implementation under test.
    modules = batching.plan(list(reversed(files)))
    assert [[item.path for item in module.files] for module in modules] == [
        ["pkg/a.py", "pkg/b.py"], ["pkg/c.py"]]


def test_index_keeps_literal_paths_as_candidates():
    files = [batching.SourceFile("a.py", "", 10_000, "", [], {"./b.py"}),
             batching.SourceFile("./b.py", "", 10_000, "", [], set())]
    assert [[f.path for f in group] for group in batching._pack_directory(files, strict=True)] == [
        ["./b.py", "a.py"]]
