from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from cbe.inventory import build_inventory, load_offsets, should_exclude_dir
from cbe.ir import CharSpan
from cbe.packets import DuplicateIdentityError, pack_inventory, packet_source, validate_packed_fragments

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _copy_fixtures(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    for name in ("python_case.py", "ts_case.ts", "js_case.js"):
        target = repo / name
        target.write_bytes((FIXTURES / name).read_bytes())
    return repo


def test_three_languages_share_inventory_and_non_overlapping_packets(tmp_path: Path) -> None:
    repo = _copy_fixtures(tmp_path)
    inventory = build_inventory(repo)
    assert set(inventory.files) == {"python_case.py", "ts_case.ts", "js_case.js"}
    for record in inventory.files.values():
        assert record.enrolled
        assert record.parse_failure is None, record.parse_failure
        assert record.state.value == "indexed"
    kinds = {symbol.kind for symbol in inventory.symbols.values()}
    assert "function" in kinds
    assert "class" in kinds
    assert "method" in kinds
    assert "module_residual" in kinds
    py_names = {
        symbol.name
        for symbol in inventory.symbols.values()
        if symbol.path == "python_case.py"
    }
    assert {"helper", "Worker", "run", "close", "format_result", "<lambda>", "test_helper_rejects_negative"} <= py_names
    ts_names = {symbol.name for symbol in inventory.symbols.values() if symbol.path == "ts_case.ts"}
    assert "Queue" in ts_names
    assert "Job" in ts_names
    assert "mapJobs" in ts_names
    assert "take" in ts_names
    js_names = {symbol.name for symbol in inventory.symbols.values() if symbol.path == "js_case.js"}
    assert "makeCounter" in js_names
    assert "run" in js_names

    packets = pack_inventory(inventory, repo=repo, window_chars=8000)
    ids = [packet.packet_id for packet in packets.packets]
    assert len(ids) == len(set(ids))
    for path, record in inventory.files.items():
        offsets = load_offsets(repo, path)
        owned = [0] * record.char_length
        file_packets = [item for item in packets.packets if item.path == path]
        assert file_packets
        for packet in file_packets:
            body = packet_source(offsets, packet)
            assert len(body) == packet.source_chars
            for span in packet.spans:
                for index in range(span.start, span.end):
                    assert owned[index] == 0, f"overlap {path}:{index}"
                    owned[index] = 1
        assert owned == [1] * record.char_length

    worker = next(symbol for symbol in inventory.symbols.values() if symbol.name == "Worker")
    run = next(symbol for symbol in inventory.symbols.values() if symbol.name == "run" and symbol.kind == "method")
    for wspan in worker.exclusive_spans:
        for rspan in run.exclusive_spans:
            assert not wspan.overlaps(rspan)
    class_text = "".join(load_offsets(repo, "python_case.py").text[s.start:s.end] for s in worker.exclusive_spans)
    assert "def run" not in class_text


def test_parse_failure_still_gets_raw_packets(tmp_path: Path) -> None:
    repo = tmp_path / "bad"
    repo.mkdir()
    (repo / "broken.py").write_text("def oops(\n", encoding="utf-8")
    inventory = build_inventory(repo)
    record = inventory.files["broken.py"]
    assert record.parse_failure is not None
    packets = pack_inventory(inventory, repo=repo)
    assert packets.packets
    assert sum(packet.source_chars for packet in packets.packets) == record.char_length


def test_fragment_count_validation_still_rejects_missing_fragment(tmp_path: Path) -> None:
    repo = _copy_fixtures(tmp_path)
    inventory = build_inventory(repo)
    packets = pack_inventory(inventory, repo=repo, window_chars=8000)
    packet = next(item for item in packets.packets if item.fragments)
    original = packet.fragments[0]
    packet.fragments = (replace(original, fragment_count=original.fragment_count + 1), *packet.fragments[1:])
    with pytest.raises(DuplicateIdentityError, match="expected .* fragments"):
        validate_packed_fragments(packets.packets, inventory)


def _assert_enrolled_partition(inventory, repo: Path) -> None:
    packets = pack_inventory(inventory, repo=repo, window_chars=8000)
    ids = [packet.packet_id for packet in packets.packets]
    assert len(ids) == len(set(ids))
    fragment_ids = [fragment.fragment_id for packet in packets.packets for fragment in packet.fragments]
    assert len(fragment_ids) == len(set(fragment_ids))
    for path, record in inventory.files.items():
        if not record.enrolled:
            continue
        offsets = load_offsets(repo, path)
        owned = [0] * record.char_length
        file_packets = [item for item in packets.packets if item.path == path]
        assert file_packets
        for packet in file_packets:
            body = packet_source(offsets, packet)
            assert len(body) == packet.source_chars
            for span in packet.spans:
                for index in range(span.start, span.end):
                    assert owned[index] == 0, f"overlap {path}:{index}"
                    owned[index] = 1
        assert owned == [1] * record.char_length


def test_python_nonascii_spans_and_nested_lambda_and_crlf_header(tmp_path: Path) -> None:
    repo = tmp_path / "py_cases"
    repo.mkdir()
    (repo / "nonascii_tail.py").write_text(
        'def greet():\n    return "你好世界"\n\nAFTER = "module level"\n',
        encoding="utf-8",
    )
    (repo / "midline.py").write_text(
        'def wrap():\n    return call("中文", lambda: 1)\n',
        encoding="utf-8",
    )
    (repo / "nested_lambda.py").write_text(
        "outer = lambda x: (lambda y: y + x)(x)\n",
        encoding="utf-8",
    )
    crlf_bytes = b"def crlf_fn(a: int) -> int:\r\n    return a\r\n\r\nTAIL = 1\r\n"
    (repo / "crlf_case.py").write_bytes(crlf_bytes)

    inventory = build_inventory(repo)
    _assert_enrolled_partition(inventory, repo)

    tail = load_offsets(repo, "nonascii_tail.py")
    greet = next(symbol for symbol in inventory.symbols.values() if symbol.name == "greet")
    greet_text = tail.text[greet.span.start:greet.span.end]
    assert greet_text.endswith('"你好世界"')
    assert "AFTER" not in greet_text
    residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "nonascii_tail.py" and symbol.kind == "module_residual"
    )
    residual_text = "".join(tail.text[span.start:span.end] for span in residual.exclusive_spans)
    assert "AFTER" in residual_text

    mid = load_offsets(repo, "midline.py")
    mid_lambda = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "midline.py" and symbol.kind == "lambda"
    )
    assert mid.text[mid_lambda.span.start:mid_lambda.span.end] == "lambda: 1"

    nested = [
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "nested_lambda.py" and symbol.kind == "lambda"
    ]
    assert len(nested) == 2
    outer, inner = sorted(nested, key=lambda item: item.span.start)
    assert outer.parent_id is None or inventory.symbols[outer.parent_id].kind == "module_residual"
    assert inner.parent_id == outer.id
    assert inner.id != outer.id
    assert outer.span.start <= inner.span.start and inner.span.end <= outer.span.end
    assert inner.extra["anchor"] == inner.span.start
    assert "<lambda>.<lambda>" in inner.qualified_name or inner.qualified_name.endswith("<lambda>")

    assert (repo / "crlf_case.py").read_bytes() == crlf_bytes
    crlf = next(symbol for symbol in inventory.symbols.values() if symbol.name == "crlf_fn")
    assert "a: int" in crlf.signature
    assert "-> int" in crlf.signature
    assert crlf.signature.startswith("def crlf_fn")
    assert not crlf.signature.endswith("a:")
    crlf_offsets = load_offsets(repo, "crlf_case.py")
    assert "\r\n" in crlf_offsets.text
    helper = next(symbol for symbol in inventory.symbols.values() if symbol.name == "greet")
    assert helper.signature.startswith("def greet")


def test_ts_overloads_and_ambient_function_are_symbols(tmp_path: Path) -> None:
    repo = tmp_path / "ts_cases"
    repo.mkdir()
    (repo / "overload.ts").write_text(
        "export function pick(a: string): string;\n"
        "export function pick(a: number): number;\n"
        "export function pick(a: unknown): unknown {\n"
        "  return a;\n"
        "}\n"
        "export const NOT_A_FN = 1;\n",
        encoding="utf-8",
    )
    (repo / "ambient.ts").write_text(
        "declare function ambient(input: string): void;\n"
        "declare const VERSION: string;\n"
        "namespace Inner {\n"
        "  export function nestedFn(x: number): number {\n"
        "    return x * 2;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (repo / "fields.ts").write_text(
        "export class Box {\n"
        "  handler = () => 1;\n"
        "  n = 2;\n"
        "}\n",
        encoding="utf-8",
    )
    inventory = build_inventory(repo)
    _assert_enrolled_partition(inventory, repo)

    picks = [
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "overload.ts" and symbol.name == "pick"
    ]
    assert len(picks) == 3
    assert len({symbol.id for symbol in picks}) == 3
    kinds = {symbol.kind for symbol in picks}
    assert "function_signature" in kinds
    assert "function" in kinds
    assert sum(1 for symbol in picks if symbol.kind == "function_signature") == 2
    assert not any(symbol.name == "NOT_A_FN" for symbol in inventory.symbols.values() if symbol.kind != "module_residual")
    residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "overload.ts" and symbol.kind == "module_residual"
    )
    overload_text = load_offsets(repo, "overload.ts").text
    residual_text = "".join(overload_text[span.start:span.end] for span in residual.exclusive_spans)
    assert "NOT_A_FN" in residual_text

    ambients = [
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "ambient.ts" and symbol.name == "ambient"
    ]
    assert len(ambients) == 1
    assert ambients[0].kind == "function_signature"
    assert ambients[0].extra.get("ambient") is True
    assert not any(
        symbol.name == "VERSION" and symbol.kind != "module_residual"
        for symbol in inventory.symbols.values()
        if symbol.path == "ambient.ts"
    )
    nested = next(symbol for symbol in inventory.symbols.values() if symbol.name == "nestedFn")
    assert nested.kind == "function"

    handler = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "fields.ts" and symbol.name == "handler"
    )
    assert handler.kind == "method"
    assert not any(
        symbol.path == "fields.ts" and symbol.name == "n" and symbol.kind == "method"
        for symbol in inventory.symbols.values()
    )


def test_js_class_field_arrow_keeps_handler_method_and_existing_shapes(tmp_path: Path) -> None:
    repo = tmp_path / "js_cases"
    repo.mkdir()
    (repo / "misc.js").write_text(
        "export function dup() { return 1; }\n"
        "export function dup() { return 2; }\n"
        "export class Bag {\n"
        "  get size() { return this.n; }\n"
        "  #hidden() { return 0; }\n"
        "  handler = () => this.n;\n"
        "}\n"
        "export const obj = {\n"
        "  run() { return '中文注释'; },\n"
        "  nested: () => () => 42,\n"
        "};\n",
        encoding="utf-8",
    )
    inventory = build_inventory(repo)
    _assert_enrolled_partition(inventory, repo)
    symbols = [symbol for symbol in inventory.symbols.values() if symbol.path == "misc.js"]
    handler = next(symbol for symbol in symbols if symbol.name == "handler")
    assert handler.kind == "method"
    size = next(symbol for symbol in symbols if symbol.name == "size")
    assert size.kind == "method"
    hidden = next(symbol for symbol in symbols if symbol.name == "#hidden")
    assert hidden.kind == "method"
    dups = [symbol for symbol in symbols if symbol.name == "dup"]
    assert len(dups) == 2
    assert dups[0].id != dups[1].id
    run = next(symbol for symbol in symbols if symbol.name == "run")
    assert run.kind == "method"


def test_inventory_keeps_own_source_in_build_dist_vendor_hidden(tmp_path: Path) -> None:
    assert should_exclude_dir("build") is False
    assert should_exclude_dir("dist") is False
    assert should_exclude_dir("vendor") is False
    assert should_exclude_dir(".hidden") is False
    assert should_exclude_dir(".git") is True
    assert should_exclude_dir(".venv") is True
    assert should_exclude_dir("node_modules") is True

    repo = tmp_path / "excl"
    (repo / "src").mkdir(parents=True)
    (repo / "build").mkdir()
    (repo / "dist").mkdir()
    (repo / "vendor").mkdir()
    (repo / ".hidden").mkdir()
    (repo / ".git" / "hooks").mkdir(parents=True)
    (repo / ".venv" / "lib").mkdir(parents=True)
    (repo / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "src" / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (repo / "build" / "gen.py").write_text("def gen():\n    return 1\n", encoding="utf-8")
    (repo / "dist" / "shipped.py").write_text("def shipped():\n    return 'real product code'\n", encoding="utf-8")
    (repo / "vendor" / "mine.js").write_text("export function mine() { return 1; }\n", encoding="utf-8")
    (repo / ".hidden" / "tool.py").write_text("def tool():\n    return 1\n", encoding="utf-8")
    (repo / "native.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (repo / "broken.py").write_text("def oops(\n", encoding="utf-8")
    (repo / ".git" / "hooks" / "secret.py").write_text("def secret():\n    return 0\n", encoding="utf-8")
    (repo / ".venv" / "lib" / "cached.py").write_text("def cached():\n    return 0\n", encoding="utf-8")
    (repo / "node_modules" / "pkg" / "index.js").write_text("export function dep() { return 0; }\n", encoding="utf-8")

    inventory = build_inventory(repo)
    own = {
        "src/ok.py",
        "build/gen.py",
        "dist/shipped.py",
        "vendor/mine.js",
        ".hidden/tool.py",
        "broken.py",
    }
    assert own <= set(inventory.files)
    for path in own:
        assert inventory.files[path].enrolled
    assert inventory.files["broken.py"].parse_failure is not None
    names = {symbol.name for symbol in inventory.symbols.values()}
    assert {"ok", "gen", "shipped", "mine", "tool"} <= names
    assert "secret" not in names
    assert "cached" not in names
    assert "dep" not in names
    assert not any(path.startswith(".git/") for path in inventory.files)
    assert not any(path.startswith(".venv/") for path in inventory.files)
    assert not any(path.startswith("node_modules/") for path in inventory.files)

    other_paths = {item["path"] for item in inventory.other_language_files}
    assert "native.c" in other_paths
    native = next(item for item in inventory.other_language_files if item["path"] == "native.c")
    assert native["reason"] == "other_language"

    excluded = {item["path"]: item for item in inventory.excluded_directories}
    assert ".git" in excluded
    assert ".venv" in excluded
    assert "node_modules" in excluded
    for path in (".git", ".venv", "node_modules"):
        item = excluded[path]
        assert item["rule"]
        assert item["reason"]
        assert "build" not in item["rule"]
    dumped = inventory.to_dict()
    dumped_paths = {item["path"] for item in dumped["excluded_directories"]}
    assert {".git", ".venv", "node_modules"} <= dumped_paths

    enrolled_chars = sum(record.char_length for path, record in inventory.files.items() if record.enrolled)
    assert inventory.s_chars == enrolled_chars
    assert inventory.s_chars >= inventory.files[".hidden/tool.py"].char_length
    assert inventory.s_chars >= inventory.files["build/gen.py"].char_length
    _assert_enrolled_partition(inventory, repo)


def _span_text(repo: Path, inventory, symbol) -> str:
    return load_offsets(repo, symbol.path).text[symbol.span.start:symbol.span.end]


def _exclusive_text(repo: Path, inventory, symbol) -> str:
    text = load_offsets(repo, symbol.path).text
    return "".join(text[span.start:span.end] for span in symbol.exclusive_spans)


def _char_owners(inventory, path: str, index: int):
    owners = []
    for symbol in inventory.symbols.values():
        if symbol.path != path:
            continue
        for span in symbol.exclusive_spans:
            if span.start <= index < span.end:
                owners.append(symbol)
    return owners


def test_python_decorator_at_belongs_to_declaration_span(tmp_path: Path) -> None:
    repo = tmp_path / "deco_cases"
    repo.mkdir()
    (repo / "stacked.py").write_text(
        "import functools\n"
        "\n"
        "@functools.lru_cache(maxsize=None)\n"
        "@staticmethod\n"
        "def cached(x: int) -> int:\n"
        "    return x\n",
        encoding="utf-8",
    )
    (repo / "paren.py").write_text(
        "def deco(fn):\n"
        "    return fn\n"
        "\n"
        "@(\n"
        "    # note\n"
        "    deco\n"
        ")\n"
        "def wrapped():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    crlf = (
        "def 装饰器(fn):\r\n"
        "    return fn\r\n"
        "\r\n"
        "@装饰器\r\n"
        "def 函数():\r\n"
        "    return 1\r\n"
        "\r\n"
        "@(\r\n"
        "    装饰器\r\n"
        ")\r\n"
        "class 盒子:\r\n"
        "    @装饰器\r\n"
        "    def 方法(self):\r\n"
        "        return 2\r\n"
    ).encode("utf-8")
    (repo / "zh_crlf.py").write_bytes(crlf)
    (repo / "header.py").write_text(
        "x = a @ b\n"
        "\n"
        "def helper(\n"
        "    value: int,\n"
        "    flag: str = \"x:y\",\n"
        ") -> int:\n"
        "    return value\n",
        encoding="utf-8",
    )
    inventory = build_inventory(repo)
    _assert_enrolled_partition(inventory, repo)

    cached = next(symbol for symbol in inventory.symbols.values() if symbol.name == "cached")
    cached_text = _span_text(repo, inventory, cached)
    assert cached_text.startswith("@functools.lru_cache")
    assert "@staticmethod" in cached_text
    assert cached.signature.startswith("def cached")
    stacked_residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "stacked.py" and symbol.kind == "module_residual"
    )
    stacked_res_text = _exclusive_text(repo, inventory, stacked_residual)
    assert "@" not in stacked_res_text
    at_owners = _char_owners(inventory, "stacked.py", cached.span.start)
    assert any(owner.id == cached.id for owner in at_owners)
    assert all(owner.kind != "module_residual" for owner in at_owners)

    wrapped = next(symbol for symbol in inventory.symbols.values() if symbol.name == "wrapped")
    wrapped_text = _span_text(repo, inventory, wrapped)
    assert wrapped_text.startswith("@(")
    assert "deco" in wrapped_text.split("def wrapped", 1)[0]
    paren_residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "paren.py" and symbol.kind == "module_residual"
    )
    assert "@" not in _exclusive_text(repo, inventory, paren_residual)

    assert (repo / "zh_crlf.py").read_bytes() == crlf
    zh_offsets = load_offsets(repo, "zh_crlf.py")
    assert "\r\n" in zh_offsets.text
    fn = next(symbol for symbol in inventory.symbols.values() if symbol.name == "函数")
    assert _span_text(repo, inventory, fn).startswith("@装饰器")
    box = next(symbol for symbol in inventory.symbols.values() if symbol.name == "盒子")
    assert _span_text(repo, inventory, box).startswith("@(")
    method = next(symbol for symbol in inventory.symbols.values() if symbol.name == "方法")
    assert _span_text(repo, inventory, method).lstrip().startswith("@装饰器")
    method_owners = _char_owners(inventory, "zh_crlf.py", method.span.start)
    assert [owner.id for owner in method_owners] == [method.id]
    zh_residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "zh_crlf.py" and symbol.kind == "module_residual"
    )
    assert "@" not in _exclusive_text(repo, inventory, zh_residual)

    helper = next(symbol for symbol in inventory.symbols.values() if symbol.name == "helper")
    helper_text = _span_text(repo, inventory, helper)
    assert helper_text.startswith("def helper(")
    assert not helper_text.startswith("@")
    header_offsets = load_offsets(repo, "header.py")
    matmul_at = header_offsets.text.index("@")
    assert matmul_at < helper.span.start
    header_residual = next(
        symbol
        for symbol in inventory.symbols.values()
        if symbol.path == "header.py" and symbol.kind == "module_residual"
    )
    header_res = _exclusive_text(repo, inventory, header_residual)
    assert "x = a @ b" in header_res
    assert header_offsets.text[matmul_at] == "@"
    matmul_owners = _char_owners(inventory, "header.py", matmul_at)
    assert any(owner.kind == "module_residual" for owner in matmul_owners)
    assert helper.id not in {owner.id for owner in matmul_owners}


def test_inventory_enrolls_owned_min_js_and_min_ts(tmp_path: Path) -> None:
    repo = tmp_path / "min_owned"
    repo.mkdir()
    js_src = (
        "export function ownedMin(value) {\n"
        "  return value + 1;\n"
        "}\n"
    )
    ts_src = (
        "export function ownedMinTs(value: number): number {\n"
        "  return value + 1;\n"
        "}\n"
    )
    (repo / "owned.min.js").write_text(js_src, encoding="utf-8")
    (repo / "owned.min.ts").write_text(ts_src, encoding="utf-8")
    (repo / "notes.md").write_text("# not enrolled this round\n", encoding="utf-8")
    inventory = build_inventory(repo)
    assert "owned.min.js" in inventory.files
    assert "owned.min.ts" in inventory.files
    assert inventory.files["owned.min.js"].enrolled
    assert inventory.files["owned.min.ts"].enrolled
    assert inventory.files["owned.min.js"].parse_failure is None
    assert inventory.files["owned.min.ts"].parse_failure is None
    assert inventory.files["owned.min.js"].language == "javascript"
    assert inventory.files["owned.min.ts"].language == "typescript"
    other_paths = {item["path"] for item in inventory.other_language_files}
    assert "owned.min.js" not in other_paths
    assert "owned.min.ts" not in other_paths
    assert not any(item.get("reason") == "generated_or_minified" for item in inventory.other_language_files)
    names = {symbol.name for symbol in inventory.symbols.values()}
    assert "ownedMin" in names
    assert "ownedMinTs" in names
    assert inventory.s_chars == (
        inventory.files["owned.min.js"].char_length
        + inventory.files["owned.min.ts"].char_length
    )
    assert "notes.md" not in inventory.files
    assert "notes.md" not in other_paths
    _assert_enrolled_partition(inventory, repo)
