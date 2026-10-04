"""Regression: ECMA walker enumerates non-body executable named children.

Fixtures live in tests/fixtures/ecma_executable_children, located from this
file via Path(__file__). Inventory and packets are consumed read-only; this
module does not modify them.
"""

from __future__ import annotations

from pathlib import Path

from cbe.inventory import build_inventory, load_offsets
from cbe.ir import FileIR, ResolutionStatus
from cbe.packets import pack_inventory, packet_source, source_for_symbol_ids
from cbe.parser import ParserSet

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ecma_executable_children"

PAYLOAD_KINDS = frozenset({"function", "method", "class", "lambda", "function_signature"})


def _copy_evidence(tmp: Path, names: tuple[str, ...]) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    for name in names:
        source = FIXTURES / name
        assert source.is_file(), source
        (repo / name).write_bytes(source.read_bytes())
    return repo


def _non_residual(inventory, path: str):
    return [
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == path and symbol.kind != "module_residual"
    ]


def _span_text(offsets, symbol) -> str:
    return offsets.text[symbol.span.start : symbol.span.end]


def _parent(inventory, symbol):
    if not symbol.parent_id:
        return None
    return inventory.symbols.get(symbol.parent_id)


def _identity(inventory, offsets, symbol) -> tuple[str, str, str | None, str | None, str]:
    parent = _parent(inventory, symbol)
    return (
        symbol.kind,
        symbol.name,
        None if parent is None else parent.kind,
        None if parent is None else parent.name,
        _span_text(offsets, symbol),
    )


def _assert_unique_ids(symbols) -> None:
    ids = [symbol.id for symbol in symbols]
    assert len(ids) == len(set(ids)), ids
    anchors = [(symbol.path, symbol.kind, symbol.span.start, symbol.name) for symbol in symbols]
    assert len(anchors) == len(set(anchors)), anchors


def _assert_exclusive_partition(inventory, repo: Path, path: str) -> None:
    record = inventory.files[path]
    owned = [0] * record.char_length
    for symbol in inventory.symbols.values():
        if symbol.path != path:
            continue
        for span in symbol.exclusive_spans:
            for index in range(span.start, span.end):
                assert owned[index] == 0, f"exclusive overlap {path}:{index} {symbol.id}"
                owned[index] = 1
    assert owned == [1] * record.char_length, {
        "path": path,
        "missing": owned.count(0),
        "repeated": sum(item > 1 for item in owned),
    }


def _assert_packet_partition(inventory, repo: Path) -> None:
    packets = pack_inventory(inventory, repo=repo, window_chars=8000)
    for path, record in inventory.files.items():
        offsets = load_offsets(repo, path)
        owned = [0] * record.char_length
        file_packets = [item for item in packets.packets if item.path == path]
        assert file_packets
        packet_ids = [item.packet_id for item in file_packets]
        assert len(packet_ids) == len(set(packet_ids)), packet_ids
        for packet in file_packets:
            body = packet_source(offsets, packet)
            assert len(body) == packet.source_chars
            for span in packet.spans:
                for index in range(span.start, span.end):
                    assert owned[index] == 0, f"packet overlap {path}:{index}"
                    owned[index] = 1
        assert owned == [1] * record.char_length


def _assert_parseset_matches_inventory(repo: Path, inventory, path: str) -> None:
    parsers = ParserSet()
    raw = (repo / path).read_bytes()
    parsed = parsers.parse_file(repo, path, raw)
    assert isinstance(parsed, FileIR), parsed
    assert parsed.record.state.value == "indexed"
    assert parsed.record.parse_failure is None
    parsed_ids = [symbol.id for symbol in parsed.symbols]
    inventory_ids = [
        symbol.id for symbol in inventory.symbols.values() if symbol.path == path
    ]
    assert parsed_ids == inventory_ids
    parsed_payload = [
        (symbol.kind, symbol.name, symbol.parent_id, symbol.span.start, symbol.span.end)
        for symbol in parsed.symbols
        if symbol.kind != "module_residual"
    ]
    inventory_payload = [
        (symbol.kind, symbol.name, symbol.parent_id, symbol.span.start, symbol.span.end)
        for symbol in inventory.symbols.values()
        if symbol.path == path and symbol.kind != "module_residual"
    ]
    assert parsed_payload == inventory_payload


def _unresolved_calls(inventory, path: str):
    return [
        relation
        for relation in inventory.relations
        if relation.get("path") == path and relation.get("kind") == "call"
    ]


def test_defaults_ts_enumerates_seven_non_residual_identities(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("defaults.ts",))
    inventory = build_inventory(repo)
    path = "defaults.ts"
    record = inventory.files[path]
    assert record.state.value == "indexed"
    assert record.parse_failure is None
    offsets = load_offsets(repo, path)
    symbols = _non_residual(inventory, path)
    _assert_unique_ids(list(inventory.symbols.values()))
    expected = [
        ("function", "choose", None, None, "function choose(cb = () => 17) { return cb(); }"),
        ("lambda", "<arrow>", "function", "choose", "() => 17"),
        (
            "class",
            "Item",
            None,
            None,
            "class Item { method(cb = function inner() { return 23; }) { return cb(); } }",
        ),
        (
            "method",
            "method",
            "class",
            "Item",
            "method(cb = function inner() { return 23; }) { return cb(); }",
        ),
        ("function", "inner", "method", "method", "function inner() { return 23; }"),
        (
            "class",
            "<class>",
            None,
            None,
            "class extends (function factory() { return Object; })() {}",
        ),
        ("function", "factory", "class", "<class>", "function factory() { return Object; }"),
    ]
    actual = [_identity(inventory, offsets, symbol) for symbol in sorted(symbols, key=lambda item: item.span.start)]
    assert actual == expected
    inner = next(symbol for symbol in symbols if symbol.name == "inner")
    factory = next(symbol for symbol in symbols if symbol.name == "factory")
    assert inner.kind == "function"
    assert factory.kind == "function"
    choose = next(symbol for symbol in symbols if symbol.name == "choose")
    arrow = next(symbol for symbol in symbols if symbol.kind == "lambda")
    assert arrow.parent_id == choose.id
    assert inner.parent_id == next(symbol for symbol in symbols if symbol.name == "method").id
    assert factory.parent_id == next(symbol for symbol in symbols if symbol.name == "<class>").id
    source, spans, _basis = source_for_symbol_ids(
        offsets,
        {symbol.id: symbol.to_dict() for symbol in inventory.symbols.values()},
        [choose.id],
    )
    assert "() => 17" not in source
    assert "function choose" in source
    assert all(not (span["start"] < arrow.span.end and arrow.span.start < span["end"]) for span in spans)
    for relation in _unresolved_calls(inventory, path):
        assert relation.get("status") == ResolutionStatus.UNRESOLVED.value
        assert relation.get("target_id") in {None, ""}
    _assert_exclusive_partition(inventory, repo, path)
    _assert_packet_partition(inventory, repo)
    _assert_parseset_matches_inventory(repo, inventory, path)


def test_defaults_js_enumerates_five_non_residual_identities(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("defaults.js",))
    inventory = build_inventory(repo)
    path = "defaults.js"
    record = inventory.files[path]
    assert record.state.value == "indexed"
    assert record.parse_failure is None
    offsets = load_offsets(repo, path)
    symbols = _non_residual(inventory, path)
    _assert_unique_ids(list(inventory.symbols.values()))
    expected = [
        ("lambda", "<arrow>", None, None, "function (cb = () => 17) { return cb(); }"),
        ("lambda", "<arrow>", "lambda", "<arrow>", "() => 17"),
        (
            "class",
            "Item",
            None,
            None,
            "class Item { method(cb = function inner() { return 23; }) { return cb(); } }",
        ),
        (
            "method",
            "method",
            "class",
            "Item",
            "method(cb = function inner() { return 23; }) { return cb(); }",
        ),
        ("function", "inner", "method", "method", "function inner() { return 23; }"),
    ]
    actual = [_identity(inventory, offsets, symbol) for symbol in sorted(symbols, key=lambda item: item.span.start)]
    assert actual == expected
    exported, default_cb = [symbol for symbol in symbols if symbol.kind == "lambda"]
    assert exported.parent_id is None or inventory.symbols[exported.parent_id].kind == "module_residual"
    assert default_cb.parent_id == exported.id
    inner = next(symbol for symbol in symbols if symbol.name == "inner")
    assert inner.kind != "method"
    source, _spans, _basis = source_for_symbol_ids(
        offsets,
        {symbol.id: symbol.to_dict() for symbol in inventory.symbols.values()},
        [exported.id],
    )
    assert "() => 17" not in source
    for relation in _unresolved_calls(inventory, path):
        assert relation.get("status") == ResolutionStatus.UNRESOLVED.value
        assert relation.get("target_id") in {None, ""}
    _assert_exclusive_partition(inventory, repo, path)
    _assert_packet_partition(inventory, repo)
    _assert_parseset_matches_inventory(repo, inventory, path)


def test_nested_destructuring_defaults_are_children_of_pack(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("nested_destruct.ts", "nested_destruct.js"))
    inventory = build_inventory(repo)
    _assert_packet_partition(inventory, repo)
    for path in ("nested_destruct.ts", "nested_destruct.js"):
        offsets = load_offsets(repo, path)
        symbols = _non_residual(inventory, path)
        _assert_unique_ids(list(inventory.symbols.values()))
        pack = next(symbol for symbol in symbols if symbol.name == "pack")
        arrow = next(symbol for symbol in symbols if symbol.kind == "lambda")
        nested = next(symbol for symbol in symbols if symbol.name == "nested")
        assert pack.kind == "function"
        assert _span_text(offsets, arrow) == "() => 1"
        assert _span_text(offsets, nested) == "function nested() { return 2; }"
        assert arrow.parent_id == pack.id
        assert nested.parent_id == pack.id
        assert nested.kind == "function"
        assert {symbol.kind for symbol in symbols} == {"function", "lambda"}
        assert len(symbols) == 3
        source, _spans, _basis = source_for_symbol_ids(
            offsets,
            {symbol.id: symbol.to_dict() for symbol in inventory.symbols.values()},
            [pack.id],
        )
        assert "() => 1" not in source
        assert "function nested" not in source
        _assert_exclusive_partition(inventory, repo, path)
        _assert_parseset_matches_inventory(repo, inventory, path)


def test_computed_key_factory_is_function_not_method(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("computed.ts", "computed.js"))
    inventory = build_inventory(repo)
    _assert_packet_partition(inventory, repo)
    for path in ("computed.ts", "computed.js"):
        offsets = load_offsets(repo, path)
        symbols = _non_residual(inventory, path)
        box = next(symbol for symbol in symbols if symbol.name == "Box")
        factory = next(symbol for symbol in symbols if symbol.name == "keyFactory")
        method = next(symbol for symbol in symbols if symbol.kind == "method")
        assert box.kind == "class"
        assert method.parent_id == box.id
        assert factory.kind == "function"
        assert factory.parent_id == method.id
        assert _span_text(offsets, factory) == "function keyFactory() { return 'run'; }"
        assert len(symbols) == 3
        for relation in _unresolved_calls(inventory, path):
            assert relation.get("status") == ResolutionStatus.UNRESOLVED.value
        _assert_exclusive_partition(inventory, repo, path)
        _assert_parseset_matches_inventory(repo, inventory, path)


def test_decorator_closures_enter_denominator(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("decorator.ts", "decorator.js"))
    inventory = build_inventory(repo)
    _assert_packet_partition(inventory, repo)
    for path in ("decorator.ts", "decorator.js"):
        offsets = load_offsets(repo, path)
        symbols = _non_residual(inventory, path)
        deco = next(symbol for symbol in symbols if symbol.name == "deco")
        decorated = next(symbol for symbol in symbols if symbol.name == "Decorated")
        method = next(symbol for symbol in symbols if symbol.name == "method")
        arrows = [symbol for symbol in symbols if symbol.kind == "lambda"]
        texts = {_span_text(offsets, symbol): symbol for symbol in arrows}
        assert set(texts) == {"() => 9", "() => 8", "() => 7"}
        assert texts["() => 9"].parent_id == deco.id
        assert texts["() => 8"].parent_id == decorated.id
        seven = texts["() => 7"]
        seven_parent = inventory.symbols[seven.parent_id]
        assert seven_parent.kind in {"class", "method"}
        assert seven_parent.name in {"Decorated", "method"}
        assert method.kind == "method"
        assert method.parent_id == decorated.id
        assert deco.kind == "function"
        for symbol in arrows:
            assert symbol.kind != "method"
        for relation in _unresolved_calls(inventory, path):
            assert relation.get("status") == ResolutionStatus.UNRESOLVED.value
        _assert_exclusive_partition(inventory, repo, path)
        _assert_parseset_matches_inventory(repo, inventory, path)


def test_pure_type_function_shapes_are_not_runtime_closures(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("types.ts",))
    inventory = build_inventory(repo)
    path = "types.ts"
    offsets = load_offsets(repo, path)
    symbols = _non_residual(inventory, path)
    kinds_names = {(symbol.kind, symbol.name) for symbol in symbols}
    assert kinds_names == {("type_alias", "Handler"), ("interface", "Sink"), ("function", "typed")}
    assert not any(symbol.kind == "lambda" for symbol in symbols)
    typed = next(symbol for symbol in symbols if symbol.name == "typed")
    children = [symbol for symbol in symbols if symbol.parent_id == typed.id]
    assert children == []
    assert "() => void" in _span_text(offsets, next(symbol for symbol in symbols if symbol.name == "Handler"))
    assert "() => number" in _span_text(offsets, typed)
    _assert_exclusive_partition(inventory, repo, path)
    _assert_packet_partition(inventory, repo)
    _assert_parseset_matches_inventory(repo, inventory, path)


def test_field_initializer_closures_and_direct_members_stay_methods(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("field_init.ts",))
    inventory = build_inventory(repo)
    path = "field_init.ts"
    offsets = load_offsets(repo, path)
    symbols = _non_residual(inventory, path)
    holder = next(symbol for symbol in symbols if symbol.name == "Holder")
    ready = next(symbol for symbol in symbols if symbol.name == "ready")
    boot = next(symbol for symbol in symbols if symbol.name == "boot")
    arrow = next(symbol for symbol in symbols if symbol.kind == "lambda")
    boot_fn = next(symbol for symbol in symbols if symbol.name == "bootFn")
    assert holder.kind == "class"
    assert ready.kind == "method"
    assert boot.kind == "method"
    assert ready.parent_id == holder.id
    assert boot.parent_id == holder.id
    assert arrow.parent_id == ready.id
    assert boot_fn.parent_id == boot.id
    assert boot_fn.kind == "function"
    assert _span_text(offsets, arrow) == "() => 1"
    assert _span_text(offsets, boot_fn) == "function bootFn() { return 2; }"
    assert len(symbols) == 5
    _assert_exclusive_partition(inventory, repo, path)
    _assert_packet_partition(inventory, repo)
    _assert_parseset_matches_inventory(repo, inventory, path)


def test_payload_children_are_subtracted_from_parent_exclusive_spans(tmp_path: Path) -> None:
    repo = _copy_evidence(tmp_path, ("defaults.ts", "defaults.js"))
    inventory = build_inventory(repo)
    for path in ("defaults.ts", "defaults.js"):
        children = [
            symbol
            for symbol in inventory.symbols.values()
            if symbol.path == path and symbol.kind in PAYLOAD_KINDS
        ]
        for parent in children:
            owned_children = [child for child in children if child.parent_id == parent.id]
            for child in owned_children:
                assert parent.span.start <= child.span.start and child.span.end <= parent.span.end
                for parent_span in parent.exclusive_spans:
                    assert not parent_span.overlaps(child.span), (parent.id, child.id)
        _assert_exclusive_partition(inventory, repo, path)
    _assert_packet_partition(inventory, repo)
