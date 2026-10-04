"""Pure projection of the committed ledger. No model calls, no source refill."""

from __future__ import annotations

import json
import posixpath
import re
from bisect import bisect_right
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from markdown_it import MarkdownIt

from cbe.ir import sha256_text
from cbe.store import LedgerStore, atomic_write_bytes, content_fingerprint, iso
from cbe.token_budget import (
    check_render_budget,
    count_frozen_source_tokens,
    count_ledger_semantic_tokens,
    count_published_text_tokens,
    count_text_tokens,
    describe_render_budget,
)

# Markdown link syntax that ignores bracket escapes: prose like
# ``typemap[type_](value)`` is stored escaped (``\\[``) and must not
# count as a page link, matching how renderers treat escaped brackets.
_LINK_RE = re.compile(r"(?<!\\)\[(?:[^\\\]]|\\.)*(?<!\\)\]\(([^)]+)\)")


def _md_escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _safe_unique(value: str) -> str:
    parts: list[str] = []
    for char in value:
        if char.isalnum() or char in "._-":
            parts.append(char)
        elif char == "/":
            parts.append("__")
        else:
            parts.append(f"_{ord(char):02X}_")
    return "".join(parts) or "_empty_"


class PageNames:
    def __init__(self) -> None:
        self._taken: dict[tuple[str, str], str] = {}
        self._names: dict[tuple[str, str], str] = {}

    def name(self, folder: str, key: str) -> str:
        cached = self._names.get((folder, key))
        if cached is not None:
            return cached
        base = _safe_unique(key)
        candidate = base
        existing = self._taken.get((folder, candidate))
        if existing is not None and existing != key:
            candidate = f"{base}_{sha256_text(key)[:10]}"
        self._taken[(folder, candidate)] = key
        self._names[(folder, key)] = candidate
        return candidate


def _symbol_link(names: PageNames, symbol_id: str) -> str:
    return f"details/{names.name('details', symbol_id)}.md"


def _group_link(names: PageNames, group_id: str) -> str:
    return f"groups/{names.name('groups', group_id)}.md"


def _file_link(names: PageNames, path: str) -> str:
    return f"files/{names.name('files', path)}.md"


def projection_fingerprint(ledger: dict) -> str:
    """Fingerprint of the projected semantic content, not the ledger revision."""
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    payload = {
        "source_revision": ledger.get("source_revision"),
        "details": {key: content_fingerprint(value) for key, value in sorted(details.items())},
        "groups": {
            key: content_fingerprint(value)
            for key, value in sorted(groups.items())
        },
        "parse_failures": [
            {"path": rec.get("path"), "state": rec.get("state")}
            for rec in ((ledger.get("inventory") or {}).get("files") or {}).values()
            if rec.get("state") in {"parse_error", "failed"}
        ],
    }
    policy = ledger.get("documentation_policy") or {}
    if policy.get("version") == "weighted-v1":
        canonical = (ledger.get("inventory") or {}).get("symbols") or {}
        payload["details"] = {
            key: content_fingerprint(details[key]) for key in sorted(canonical) if key in details
        }
        payload["documentation_policy"] = content_fingerprint(policy)
        payload["render_template"] = "weighted-v1/1"
        payload["inventory_symbols"] = content_fingerprint(canonical)
        payload["inventory_files"] = content_fingerprint((ledger.get("inventory") or {}).get("files") or {})
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def render(run_dir: Path, output_dir: Path | None = None) -> dict:
    store = LedgerStore(run_dir)
    ledger = store.open()
    profile = (ledger.get("documentation_policy") or {}).get("version")
    if profile == "module-first-v2":
        from cbe.module_first_render import render_module_plan

        plan = json.loads((Path(run_dir) / "module_plan.json").read_text(encoding="utf-8"))
        if ledger.get("module_workflow_version"):
            from cbe.module_workflow import accepted_package

            explanations = accepted_package(ledger)
        else:
            explanations_path = Path(run_dir) / "module_explanations.json"
            explanations = (
                json.loads(explanations_path.read_text(encoding="utf-8"))
                if explanations_path.exists() else None
            )
        destination = Path(output_dir or ledger.get("reader_output_dir") or Path(run_dir) / "render").resolve()
        manifest = render_module_plan(ledger, plan, destination, explanations,
                                      run_dir=run_dir)
        def record_destination(current: dict) -> dict:
            if current["source_revision"] != ledger["source_revision"]:
                raise ValueError("source changed while recording reader output")
            current["reader_output_dir"] = str(destination)
            current["reader_render_diagnostics"] = {key: manifest[key] for key in (
                "source_revision", "plan_sha256", "facts_sha256", "explanations_sha256")}
            current["reader_render_diagnostics"]["syntax_projection_accounting"] = manifest["syntax_projection_accounting"]
            return current
        store.mutate(record_destination)
        return manifest
    if output_dir is not None:
        raise ValueError("--output is supported for module-first-v2 runs")
    if profile == "weighted-v1":
        return _render_weighted(run_dir, store, ledger)
    staging = run_dir / ".render-staging"
    if staging.exists():
        import shutil

        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    symbols = (ledger.get("inventory") or {}).get("symbols") or {}
    graph = ledger.get("graph") or {}
    files = (ledger.get("inventory") or {}).get("files") or {}
    names = PageNames()

    (staging / "details").mkdir()
    (staging / "groups").mkdir()
    (staging / "files").mkdir()

    broken: list[str] = []
    known_ids: set[str] = set(details) | set(groups)
    known_by_length = sorted(known_ids, key=len, reverse=True)

    def split_dep(dep) -> tuple[str | None, str]:
        """Producer dependencies are often '<id> <prose role>'. Split when possible."""
        if not isinstance(dep, str):
            dep_id = dep.get("symbol_id") if isinstance(dep, dict) else None
            return (dep_id or None), ""
        if dep in known_ids:
            return dep, ""
        for candidate in known_by_length:
            if dep.startswith(candidate) and len(dep) > len(candidate) and dep[len(candidate)] in " :—-–(":
                return candidate, dep[len(candidate):].strip()
        return None, dep

    def rewrite_links(text: str) -> str:
        """Agents link ids in prose bodies; rewrite known ids to their pages."""
        if not text:
            return text

        def repl(match: "re.Match[str]") -> str:
            target = match.group(1).split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", ".", "/")):
                return match.group(0)
            if target in groups:
                return match.group(0).replace(f"]({match.group(1)})", f"](../{_group_link(names, target)})")
            if target in details:
                return match.group(0).replace(f"]({match.group(1)})", f"](../{_symbol_link(names, target)})")
            return match.group(0)

        return _LINK_RE.sub(repl, text)

    for symbol_id, detail in details.items():
        symbol = symbols.get(symbol_id) or {}
        path = staging / _symbol_link(names, symbol_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        deps = detail.get("dependencies") or []
        dep_links = []
        if isinstance(deps, list):
            for dep in deps:
                dep_id, prose = split_dep(dep)
                label = f"{dep_id} {prose}".strip() if dep_id else prose
                if dep_id in details:
                    dep_links.append(f"- [{label}](../{_symbol_link(names, dep_id)})")
                elif dep_id in groups:
                    dep_links.append(f"- group [{label}](../{_group_link(names, dep_id)})")
                elif dep_id is None:
                    dep_links.append(f"- {prose}")
                else:
                    broken.append(f"detail {symbol_id} -> {dep_id}")
                    dep_links.append(f"- {label} (unresolved)")
        body = "\n".join(
            [
                f"# {symbol.get('kind', 'symbol')} `{symbol.get('name', symbol_id)}`",
                "",
                f"- id: `{symbol_id}`",
                f"- path: `{symbol.get('path', '')}`",
                f"- ledger revision: {ledger.get('ledger_revision')}",
                f"- stale: {bool((detail.get('provenance') or {}).get('stale'))}",
                "",
                "## Behavior",
                "",
                str(detail.get("behavior") or ""),
                "",
                "## Inputs / outputs",
                "",
                f"```\n{json.dumps(detail.get('inputs_outputs'), ensure_ascii=False, indent=2)}\n```",
                "",
                "## Effects",
                "",
                f"```\n{json.dumps(detail.get('effects'), ensure_ascii=False, indent=2)}\n```",
                "",
                "## Failures",
                "",
                f"```\n{json.dumps(detail.get('failures'), ensure_ascii=False, indent=2)}\n```",
                "",
                "## Dependencies",
                "",
                "\n".join(dep_links) or "(none listed)",
                "",
                "## Unresolved",
                "",
                f"```\n{json.dumps(detail.get('unresolved'), ensure_ascii=False, indent=2)}\n```",
                "",
                "[Back to index](../INDEX.md)",
            ]
        )
        path.write_text(body + "\n", encoding="utf-8")

    for group_id, group in groups.items():
        path = staging / _group_link(names, group_id)
        members = []
        for member in group.get("member_ids") or []:
            if member in details:
                members.append(f"- [{member}](../{_symbol_link(names, member)})")
            elif member in groups:
                broken.append(f"group {group_id} member {member} is a group; member_ids must be details")
                members.append(f"- {member} (type error)")
            else:
                broken.append(f"group {group_id} member {member}")
                members.append(f"- {member} (missing)")
        children = []
        for child in group.get("children") or []:
            if child in groups:
                children.append(f"- [{child}](../{_group_link(names, child)})")
            elif child in details:
                broken.append(f"group {group_id} child {child} is a detail; children must be groups")
                children.append(f"- {child} (type error)")
            else:
                broken.append(f"group {group_id} child {child}")
                children.append(f"- {child} (missing)")
        extra = group.get("extra") if isinstance(group.get("extra"), dict) else {}
        replaced = extra.get("replaced_by")
        header = [
                    f"# {group_id}",
                    "",
                    f"- question: {group.get('question_answered') or ''}",
                    f"- grouping reason: {group.get('grouping_reason') or ''}",
                    f"- partial: {group.get('partial')}",
                    f"- stale: {bool(extra.get('stale'))}",
                    f"- version: {group.get('version')}",
        ]
        if replaced:
            header.append(f"- replaced_by: `{replaced}`")
        path.write_text(
            "\n".join(
                header
                + [
                    "",
                    "## Body",
                    "",
                    rewrite_links(group.get("body") or "(body not yet written)"),
                    "",
                    "## Members",
                    "",
                    "\n".join(members) or "(none)",
                    "",
                    "## Children",
                    "",
                    "\n".join(children) or "(none)",
                    "",
                    "## Entry routes",
                    "",
                    "\n".join(f"- {item}" for item in (group.get("entry_routes") or [])) or "(none)",
                    "",
                    "[Back to index](../INDEX.md)",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    by_file: dict[str, list[str]] = {}
    for symbol_id, symbol in symbols.items():
        by_file.setdefault(symbol.get("path") or "", []).append(symbol_id)
    for path in files:
        by_file.setdefault(path, [])
    for path, symbol_ids in by_file.items():
        record = files.get(path) or {}
        lines = [f"# `{path}`", ""]
        if record.get("parse_failure"):
            lines += [
                "This file has a parse failure. There is no invented structure.",
                "",
                "```",
                json.dumps(record.get("parse_failure"), ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        elif not symbol_ids:
            lines += ["This enrolled file has no extracted symbols.", ""]
        else:
            lines += ["Symbols in this file:", ""]
        for symbol_id in symbol_ids:
            symbol = symbols[symbol_id]
            if symbol_id in details:
                lines.append(
                    f"- [{symbol.get('kind')} {symbol.get('name')}](../{_symbol_link(names, symbol_id)})"
                )
            else:
                lines.append(f"- {symbol.get('kind')} {symbol.get('name')} (no Detail yet)")
        target = staging / _file_link(names, path)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    index_lines = [
        "# Codebase Explorer",
        "",
        f"Run `{ledger.get('run_id')}` · source revision `{ledger.get('source_revision')}`",
        "",
        "This index is a projection of the ledger. It is not a second completion status.",
        "",
        "## What this repository is for",
        "",
        _opening_paragraph(ledger, groups, details),
        "",
        "## How to start",
        "",
        "1. Read the groups below (imported architecture). Folder names are an index, not the architecture.",
        "2. Follow links to any semantic layer page, then to function Detail pages.",
        "3. Use `python -m cbe query --run-dir <dir> --id <id>` to retrieve a record.",
        "",
        "## Key runtime flows (from the graph entries)",
        "",
    ]
    entries = list(graph.get("entries") or [])
    entries_total = int(graph.get("entries_total") or len(entries))
    shown_entries = entries[:12]
    for entry in shown_entries:
        if entry in details:
            index_lines.append(f"- [{entry}]({_symbol_link(names, entry)})")
        else:
            index_lines.append(f"- `{entry}` (Detail pending)")
    if entries_total > len(shown_entries):
        index_lines.append(
            f"- … {entries_total - len(shown_entries)} more entries "
            f"(entries_total={entries_total}; page via `cbe status --json` graph/frontier)"
        )
    index_lines += ["", "## Architecture map", ""]
    index_lines += _architecture_section(ledger, groups, names)
    index_lines += ["", "## Module dependency graph", ""]
    index_lines += _module_graph_section(ledger, groups, details, names)
    index_lines += ["", "## Semantic groups", ""]
    current_groups = [
        (group_id, group)
        for group_id, group in sorted(groups.items())
        if not ((group.get("extra") or {}).get("replaced_by"))
    ]
    replaced_groups = [
        (group_id, group)
        for group_id, group in sorted(groups.items())
        if (group.get("extra") or {}).get("replaced_by")
    ]
    if not groups:
        index_lines.append(
            "No architecture groups imported yet. The runner will not invent folder or connected-component groups. "
            "Use `cbe claim --kind group --input-ids-file` and `cbe import-result`."
        )
    elif not current_groups:
        index_lines.append("No current architecture groups. Replaced groups remain queryable below.")
    else:
        for group_id, group in current_groups:
            title = group.get("question_answered") or group_id
            index_lines.append(f"- [{title}]({_group_link(names, group_id)})")
    if replaced_groups:
        index_lines += [
            "",
            "## Replaced groups",
            "",
            "These groups were replaced. They remain in the ledger and are queryable; they are not current navigation.",
            "",
        ]
        for group_id, group in replaced_groups:
            title = group.get("question_answered") or group_id
            replaced = (group.get("extra") or {}).get("replaced_by")
            index_lines.append(
                f"- [{title}]({_group_link(names, group_id)}) — replaced by `{replaced}`"
            )
    index_lines += ["", "## File tree (second index)", ""]
    for path in sorted(files):
        index_lines.append(f"- [`{path}`]({_file_link(names, path)})")
    index_lines += ["", "## Unknowns", ""]
    unknown = graph.get("unknown_edges") or []
    unknown_total = int(graph.get("unknown_edges_total") or len(unknown))
    index_lines.append(f"Graph edges without a resolved in-repo target: {unknown_total}")
    parse_failures = [
        f"- `{path}`: {(record.get('parse_failure') or {}).get('message')}"
        for path, record in files.items()
        if record.get("parse_failure")
    ]
    if parse_failures:
        index_lines += ["", "Parser failures:", ""] + parse_failures
    (staging / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    broken.extend(_broken_markdown_links(staging))
    if broken:
        extra = ["", "## Broken links", ""] + [f"- {item}" for item in broken]
        index_path = staging / "INDEX.md"
        index_path.write_text(index_path.read_text(encoding="utf-8") + "\n".join(extra) + "\n", encoding="utf-8")

    manifest = {
        "ledger_revision": ledger.get("ledger_revision"),
        "rendered_at": iso(),
        "broken_links": broken,
        "page_count": sum(1 for _ in staging.rglob("*.md")),
        "page_names": {
            "files": {key: names.name("files", key) for key in files},
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    import shutil

    live = run_dir / "render"
    previous = run_dir / "render.prev"
    if live.exists():
        if previous.exists():
            shutil.rmtree(previous)
        live.rename(previous)
    staging.rename(live)

    def bump(current: dict) -> dict:
        fingerprint = projection_fingerprint(current)
        current["render_revision"] = fingerprint
        current["render_content_fingerprint"] = fingerprint
        return current

    store.mutate(bump)
    return manifest


def _compact_page(folder: str, key: str) -> str:
    return f"{folder}/{folder[0]}-{sha256_text(key)[:16]}.md"


def _heading_name(value: str) -> str:
    """Keep a short visible heading whose Markdown slug is predictable."""
    return re.sub(r"[^\w .-]", "", value).strip() or "symbol"


def _heading_slug(value: str) -> str:
    return re.sub(r"[^\w\s-]", "", value.lower()).replace(" ", "-") or "symbol"


def _compact_tier(ledger: dict, symbol_id: str) -> str:
    policy = ledger.get("documentation_policy") or {}
    item = (policy.get("symbols") or {}).get(symbol_id) or {}
    tier = item.get("tier")
    if tier not in {"brief", "standard", "deep"}:
        raise ValueError(f"weighted render has no valid frozen tier for {symbol_id}")
    return tier


def _source_line_numbers(ledger: dict, symbols: dict) -> dict[str, int]:
    """Derive line labels from hash-verified source; never infer a source span."""
    from cbe.ir import sha256_bytes

    root = Path(ledger["repo_root"])
    files = (ledger.get("inventory") or {}).get("files") or {}
    by_file: dict[str, list[tuple[str, int]]] = {}
    for symbol_id, symbol in symbols.items():
        span = symbol.get("span") or {}
        by_file.setdefault(symbol.get("path") or "", []).append((symbol_id, int(span.get("start") or 0)))
    lines: dict[str, int] = {}
    for relative, items in by_file.items():
        record = files.get(relative)
        if record is None:
            raise ValueError(f"symbol path has no frozen file: {relative}")
        raw = (root / relative).read_bytes()
        if sha256_bytes(raw) != record.get("content_hash"):
            raise ValueError(f"frozen source hash mismatch for {relative}")
        text = raw.decode("utf-8")
        starts = [0] + [idx + 1 for idx, char in enumerate(text) if char == "\n"]
        for symbol_id, start in items:
            if start < 0 or start > len(text):
                raise ValueError(f"symbol span outside frozen source: {symbol_id}")
            lines[symbol_id] = bisect_right(starts, start)
    return lines


def _compact_label(value: str) -> str:
    return _md_escape(re.sub(r"\s+", " ", value).strip()).replace("[", "\\[").replace("]", "\\]")


def _relative_target(page: str, target: str) -> str:
    path, separator, anchor = target.partition("#")
    start = posixpath.dirname(page) or "."
    relative = posixpath.relpath(path, start)
    return f"{relative}#{anchor}" if separator else relative


_WIKI_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
_HTML_MEDIA_TAGS = frozenset({"img", "picture", "video", "svg", "audio", "canvas", "object", "embed", "iframe", "source"})


class _MediaParser(HTMLParser):
    """Recognize complete HTML media tags, not prose '<' or comments."""

    def __init__(self):
        super().__init__()
        self.has_media = False

    def handle_starttag(self, tag, attrs):
        if tag in _HTML_MEDIA_TAGS:
            self.has_media = True

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")


def _outside_code_lines(text: str):
    """Yield non-fenced lines with inline code spans masked for link checks."""
    marker = ""
    width = 0
    for line in text.splitlines():
        fence = _FENCE_RE.match(line)
        if fence:
            token = fence.group(1)
            if not marker:
                marker, width = token[0], len(token)
            elif token[0] == marker and len(token) >= width:
                marker, width = "", 0
            continue
        if not marker:
            yield _INLINE_CODE_RE.sub("", line)


def _rewrite_references(text: str, page: str, targets: dict[str, str], broken: list[str]) -> str:
    """Resolve record IDs in generated prose relative to its actual page."""
    marker = ""
    width = 0
    output: list[str] = []
    for line in text.splitlines():
        fence = _FENCE_RE.match(line)
        if fence:
            token = fence.group(1)
            if not marker:
                marker, width = token[0], len(token)
            elif token[0] == marker and len(token) >= width:
                marker, width = "", 0
            output.append(line)
            continue
        if marker:
            output.append(line)
            continue

        def rewrite_part(part: str) -> str:
            def wiki(match: re.Match[str]) -> str:
                raw = match.group(1)
                key, _, label = raw.partition("|")
                key = key.strip()
                if key not in targets:
                    broken.append(f"{page} -> [[{raw}]] (unknown record)")
                    return match.group(0)
                return f"[{_compact_label(label.strip() or key)}]({_relative_target(page, targets[key])})"

            part = _WIKI_RE.sub(wiki, part)

            def markdown(match: re.Match[str]) -> str:
                raw = match.group(1)
                key, separator, fragment = raw.partition("#")
                if key not in targets:
                    return match.group(0)
                target = targets[key]
                if separator and "#" not in target:
                    target += f"#{fragment}"
                return match.group(0).replace(f"]({raw})", f"]({_relative_target(page, target)})")

            return _LINK_RE.sub(markdown, part)

        pieces: list[str] = []
        offset = 0
        for match in _INLINE_CODE_RE.finditer(line):
            pieces.append(rewrite_part(line[offset:match.start()]))
            pieces.append(match.group(0))
            offset = match.end()
        pieces.append(rewrite_part(line[offset:]))
        output.append("".join(pieces))
    return "\n".join(output)


def _weighted_target_index(ledger: dict, current: dict, *, navigation_only: bool = False) -> dict:
    """Canonical weighted link targets, shared by rendering and on-demand resolve."""
    inventory = ledger.get("inventory") or {}
    symbols = inventory.get("symbols") or {}
    files = inventory.get("files") or {}
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    file_targets = {path: _compact_page("files", path) for path in files}
    group_targets = {group_id: _compact_page("groups", group_id) for group_id in current}
    if len(set(file_targets.values())) != len(file_targets) or len(set(group_targets.values())) != len(group_targets):
        raise ValueError("compact page hash collision")
    detail_ids = {
        symbol_id for symbol_id in symbols
        if _compact_tier(ledger, symbol_id) == "deep"
        and (symbol_id in details or navigation_only)
    }
    key_ids = {
        symbol_id for symbol_id in symbols
        if _compact_tier(ledger, symbol_id) in {"standard", "deep"}
    }
    by_file: dict[str, list[str]] = {path: [] for path in files}
    for symbol_id, symbol in symbols.items():
        path = symbol.get("path") or ""
        if path not in by_file:
            raise ValueError(f"symbol path has no frozen file: {symbol_id}")
        by_file[path].append(symbol_id)
    for symbol_ids in by_file.values():
        symbol_ids.sort(key=lambda sid: ((symbols[sid].get("span") or {}).get("start") or 0, sid))
    anchors: dict[str, str] = {}
    for symbol_ids in by_file.values():
        occurrences: dict[str, int] = {}
        for symbol_id in symbol_ids:
            if symbol_id in detail_ids:
                continue
            base = _heading_slug(_heading_name(str(symbols[symbol_id].get("name") or "symbol")))
            ordinal = occurrences.get(base, 0)
            anchors[symbol_id] = base if ordinal == 0 else f"{base}-{ordinal}"
            occurrences[base] = ordinal + 1
    symbol_targets = {
        symbol_id: (
            _compact_page("details", symbol_id) if symbol_id in detail_ids
            else f"{file_targets[symbol['path']]}#{anchors[symbol_id]}"
        )
        for symbol_id, symbol in symbols.items()
    }
    if len(set(_compact_page("details", sid) for sid in detail_ids)) != len(detail_ids):
        raise ValueError("compact detail page hash collision")
    targets = {**symbol_targets, **group_targets}
    for group_id, group in groups.items():
        if group_id in current:
            continue
        successor = (group.get("extra") or {}).get("replaced_by")
        seen = {group_id}
        while successor in groups and successor not in seen and successor not in current:
            seen.add(successor)
            successor = ((groups[successor].get("extra") or {}).get("replaced_by"))
        if successor in group_targets:
            targets[group_id] = group_targets[successor]
    return {
        "file_targets": file_targets,
        "group_targets": group_targets,
        "detail_ids": detail_ids,
        "key_ids": key_ids,
        "by_file": by_file,
        "anchors": anchors,
        "symbol_targets": symbol_targets,
        "targets": targets,
    }


def resolve_reader_target(ledger: dict, ident: str) -> str | None:
    """Resolve one weighted ledger ID to its reader page without publishing."""
    if (ledger.get("documentation_policy") or {}).get("version") != "weighted-v1":
        return None
    inventory = ledger.get("inventory") or {}
    symbols = inventory.get("symbols") or {}
    files = inventory.get("files") or {}
    groups = ledger.get("groups") or {}
    if ident not in symbols and ident not in files and ident not in groups:
        return None
    current = {gid: group for gid, group in groups.items() if not ((group.get("extra") or {}).get("replaced_by"))}
    index = _weighted_target_index(ledger, current)
    return index["targets"].get(ident) or index["file_targets"].get(ident)


def _write_weighted_pages(ledger: dict, staging: Path | None, *, navigation_only: bool = False) -> dict:
    """Write one compact description per symbol and the module navigation."""
    inventory = ledger.get("inventory") or {}
    symbols = inventory.get("symbols") or {}
    files = inventory.get("files") or {}
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    pending_details = {
        sid for sid in symbols
        if sid not in details or any(
            (details[sid].get("provenance") or {}).get(flag)
            for flag in ("stale", "historical", "incomplete")
        )
    }
    current = {gid: group for gid, group in groups.items() if not ((group.get("extra") or {}).get("replaced_by"))}
    parent_for = {
        child: gid
        for gid, group in current.items()
        for child in (group.get("children") or [])
        if child in current
    }
    pending_groups = {
        gid for gid, group in current.items()
        if (group.get("extra") or {}).get("stale")
        or (group.get("extra") or {}).get("body_stale")
        or pending_details.intersection((group.get("member_ids") or []) + (group.get("entry_routes") or []))
    }
    frontier = list(pending_groups)
    while frontier:
        gid = frontier.pop()
        parent = current[gid].get("parent_id") or parent_for.get(gid)
        if parent in current and parent not in pending_groups:
            pending_groups.add(parent)
            frontier.append(parent)
    navigation_tokens = 0

    def write_page(relative: str, lines: list[str]) -> None:
        nonlocal navigation_tokens
        body = "\n".join(lines) + "\n"
        if staging is None:
            navigation_tokens += count_text_tokens(body)
        else:
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    if staging is not None:
        for folder in ("files", "groups", "details"):
            (staging / folder).mkdir(parents=True, exist_ok=True)
    line_numbers = _source_line_numbers(ledger, symbols)
    target_index = _weighted_target_index(ledger, current, navigation_only=navigation_only)
    file_targets = target_index["file_targets"]
    group_targets = target_index["group_targets"]
    detail_ids = target_index["detail_ids"]
    key_ids = target_index["key_ids"]
    by_file = target_index["by_file"]
    symbol_targets = target_index["symbol_targets"]
    targets = target_index["targets"]
    broken: list[str] = []

    def link(page: str, record_id: str, label: str) -> str:
        target = targets.get(record_id)
        if target is None:
            broken.append(f"{page} -> {record_id} (unknown record)")
            return _compact_label(label)
        return f"[{_compact_label(label)}]({_relative_target(page, target)})"

    for path, symbol_ids in sorted(by_file.items()):
        page = file_targets[path]
        lines = [f"# `{path}`", ""]
        record = files[path]
        if record.get("parse_failure"):
            lines.append(f"Parse failure: {_compact_label((record['parse_failure'] or {}).get('message') or 'unknown')}")
        for symbol_id in symbol_ids:
            symbol = symbols[symbol_id]
            name = str(symbol.get("name") or symbol_id)
            line = line_numbers[symbol_id]
            if symbol_id in detail_ids:
                lines.append(f"- {link(page, symbol_id, name)} · L{line}")
            else:
                detail = details.get(symbol_id) or {}
                pending = symbol_id in pending_details
                behavior = "" if navigation_only or pending else _compact_label(str(detail.get("behavior") or ""))
                locator = f"L{line}" + (
                    ": Pending verification." if pending and not navigation_only
                    else f": {behavior}" if behavior else ""
                )
                lines += [f"### {_heading_name(name)}", locator, ""]
                if not navigation_only and not pending and symbol_id in key_ids:
                    for field, label in (("effects", "Effects"), ("failures", "Failures"), ("unresolved", "Unknown")):
                        value = detail.get(field)
                        if value not in (None, "", [], {}):
                            rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                            lines.append(f"- {label}: {_rewrite_references(str(rendered), page, targets, broken)}")
                    lines.append("")
        write_page(page, lines)

    file_index = ["# Source files", ""]
    for path in sorted(files):
        file_index.append(f"- [{_compact_label(path)}]({file_targets[path]})")
    write_page("FILES.md", file_index)

    for symbol_id in sorted(detail_ids):
        symbol = symbols[symbol_id]
        pending = symbol_id in pending_details
        detail = {} if navigation_only or pending else (details.get(symbol_id) or {})
        page = symbol_targets[symbol_id]
        name = str(symbol.get("name") or symbol_id)
        lines = [f"# `{_compact_label(name)}`", "", f"Source: `{symbol['path']}:L{line_numbers[symbol_id]}`"]
        if pending and not navigation_only:
            lines += ["", "> Pending verification: prior description withheld; inspect the source."]
        behavior = str(detail.get("behavior") or "").strip()
        if behavior:
            lines += ["", _rewrite_references(behavior, page, targets, broken)]
        for field, label in (
            ("inputs_outputs", "I/O"),
            ("effects", "Effects"),
            ("failures", "Failures"),
            ("unresolved", "Unknown"),
        ):
            value = detail.get(field)
            if value not in (None, "", [], {}):
                rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                lines.append(f"- {label}: {_rewrite_references(str(rendered), page, targets, broken)}")
        deps = detail.get("dependencies") or []
        if isinstance(deps, list) and deps:
            rendered_deps = []
            for dependency in deps:
                if isinstance(dependency, dict):
                    dep_id = dependency.get("symbol_id") or dependency.get("group_id")
                    prose = dependency.get("role") or ""
                else:
                    raw = str(dependency)
                    dep_id = raw if raw in targets else None
                    prose = ""
                    if dep_id is None:
                        for offset in (match.start() for match in re.finditer(r"\s", raw)):
                            if raw[:offset] in targets:
                                dep_id, prose = raw[:offset], raw[offset:].strip(" :—-–()")
                                break
                    if dep_id is None:
                        prose = raw
                if dep_id in targets:
                    dep_label = (symbols.get(dep_id) or {}).get("name") or dep_id
                    rendered_deps.append(link(page, dep_id, str(dep_label)) + (f" {prose}" if prose else ""))
                elif prose:
                    rendered_deps.append(_compact_label(str(prose)))
            if rendered_deps:
                lines.append("- Uses: " + "; ".join(rendered_deps))
        write_page(page, lines)

    root_ids = [gid for gid, group in current.items() if not group.get("parent_id")]
    root_id = root_ids[0] if len(root_ids) == 1 else None
    for group_id, group in sorted(current.items()):
        page = group_targets[group_id]
        title = group_id if group_id in pending_groups else (group.get("question_answered") or group_id)
        lines = [f"# {_compact_label(str(title))}"]
        body = "" if navigation_only or group_id == root_id or group_id in pending_groups else str(group.get("body") or "").strip()
        if group_id in pending_groups:
            lines += ["", "> Pending refresh: this module explanation is withheld until source review completes."]
        elif body:
            lines += ["", _rewrite_references(body, page, targets, broken)]
        children = group.get("children") or []
        if children:
            lines += ["", "## Modules"]
            for child in children:
                lines.append(f"- {link(page, child, child)}")
        members = group.get("member_ids") or []
        entry_routes = group.get("entry_routes") or []
        # The file index owns complete coverage. Group pages point to a small
        # set of entry symbols, rather than repeating every member link.
        selected: list[str] = []
        brief_routes = 0
        for sid in [*entry_routes, *(sid for sid in members if sid in key_ids)]:
            if sid not in symbols or sid in selected:
                continue
            if sid not in key_ids:
                if brief_routes >= 3:
                    continue
                brief_routes += 1
            selected.append(sid)
            if len(selected) >= 12:
                break
        if selected:
            lines += ["", "## Key symbols"]
            for sid in selected:
                lines.append(f"- {link(page, sid, str(symbols[sid].get('name') or sid))}")
        elif members and ((group.get("extra") or {}).get("presentation") == "navigation"):
            # A navigation-only group with brief members still needs a local
            # way into source. Complete membership remains in the ledger.
            member_files = sorted({symbols[sid]["path"] for sid in members if sid in symbols})
            if member_files:
                lines += ["", "## Source entry"]
                for source_path in member_files[:3]:
                    lines.append(
                        f"- [{_compact_label(Path(source_path).name)}]({_relative_target(page, file_targets[source_path])})"
                    )
                if len(member_files) > 3:
                    lines.append(f"- [All source files]({_relative_target(page, 'FILES.md')})")
        for sid in members:
            if sid not in symbols:
                broken.append(f"{page} -> member {sid} (unknown symbol)")
        write_page(page, lines)

    index = ["# Codebase Explorer", "", "[Source files](FILES.md)"]
    if root_id:
        root = current[root_id]
        body = "" if navigation_only or root_id in pending_groups else str(root.get("body") or "").strip()
        if root_id in pending_groups:
            index += ["", "> Pending refresh: the module summary is withheld until source review completes."]
        elif body:
            index += ["", _rewrite_references(body, "INDEX.md", targets, broken)]
        root_label = root_id if root_id in pending_groups else str(root.get("question_answered") or root_id)
        index += ["", "## Modules", "", f"- {link('INDEX.md', root_id, root_label)}"]
        top = [gid for gid in (root.get("children") or []) if gid in current]
    else:
        top = sorted(gid for gid, group in current.items() if not group.get("parent_id"))
        if top:
            index += ["", "## Modules"]
    for gid in top:
        group = current[gid]
        label = gid if gid in pending_groups else str(group.get("question_answered") or gid)
        index.append(f"- {link('INDEX.md', gid, label)}")
    write_page("INDEX.md", index)
    return {
        "navigation_tokens": navigation_tokens,
        "symbol_targets": symbol_targets,
        "file_targets": file_targets,
        "group_targets": group_targets,
        "broken_references": broken,
        "pending_detail_ids": sorted(pending_details),
        "pending_group_ids": sorted(pending_groups),
    }


def estimate_weighted_navigation_tokens(ledger: dict) -> dict[str, int | str]:
    """Lower bound for fixed reader navigation before model production begins."""
    if (ledger.get("documentation_policy") or {}).get("version") != "weighted-v1":
        raise ValueError("navigation preflight requires weighted-v1 policy")
    source_tokens = count_frozen_source_tokens(ledger)
    navigation_tokens = int(_write_weighted_pages(ledger, None, navigation_only=True)["navigation_tokens"])
    return {
        "tokenizer": "o200k_base",
        "source_tokens": source_tokens,
        "navigation_tokens": navigation_tokens,
        "limit_tokens": source_tokens // 2,
        "remaining_tokens": source_tokens // 2 - navigation_tokens,
    }


def _write_counted_manifest(staging: Path, manifest: dict, source_tokens: int) -> int:
    """Solve the manifest's own token count before the publication gate."""
    path = staging / "manifest.json"
    budget = manifest["token_budget"]
    seen: set[str] = set()
    cycle = False
    for _ in range(16):
        serialized = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n"
        path.write_text(serialized, encoding="utf-8")
        if serialized in seen:
            cycle = True
            break
        seen.add(serialized)
        actual = count_published_text_tokens(staging)
        ratio = f"{actual / source_tokens:.6f}" if source_tokens else ("0.000000" if not actual else "inf")
        query_only = int(budget.get("query_only_tokens") or 0)
        effective = actual + query_only
        effective_ratio = f"{effective / source_tokens:.6f}" if source_tokens else ("0.000000" if not effective else "inf")
        target_status = (
            "within_target" if source_tokens and effective <= source_tokens * 0.5 else
            "explainable_overage" if source_tokens and effective <= source_tokens * 0.55 else
            "above_guidance"
        )
        if (
            budget["published_tokens"] == actual
            and budget["ratio"] == ratio
            and budget.get("effective_document_tokens", effective) == effective
            and budget.get("effective_ratio", effective_ratio) == effective_ratio
            and budget.get("target_status", target_status) == target_status
        ):
            return actual
        budget["published_tokens"] = actual
        budget["ratio"] = ratio
        if "query_only_tokens" in budget:
            budget["effective_document_tokens"] = effective
            budget["effective_ratio"] = effective_ratio
        if "target_status" in budget:
            budget["target_status"] = target_status
    if cycle:
        # Status strings near 50/55% can make the self-count oscillate. Change
        # only JSON serialization whitespace; count it rather than exclude it.
        actual = count_published_text_tokens(staging)
        other_tokens = actual - count_text_tokens(path.read_text(encoding="utf-8"))
        for padding in range(17):
            for candidate in range(max(0, actual - 16), actual + 17):
                effective = candidate + int(budget.get("query_only_tokens") or 0)
                budget["published_tokens"] = candidate
                budget["ratio"] = f"{candidate / source_tokens:.6f}" if source_tokens else ("0.000000" if not candidate else "inf")
                if "effective_document_tokens" in budget:
                    budget["effective_document_tokens"] = effective
                if "effective_ratio" in budget:
                    budget["effective_ratio"] = f"{effective / source_tokens:.6f}" if source_tokens else ("0.000000" if not effective else "inf")
                if "target_status" in budget:
                    budget["target_status"] = (
                        "within_target" if source_tokens and effective <= source_tokens * 0.5 else
                        "explainable_overage" if source_tokens and effective <= source_tokens * 0.55 else
                        "above_guidance")
                serialized = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n" + "\t\n" * padding
                if other_tokens + count_text_tokens(serialized) != candidate:
                    continue
                path.write_text(serialized, encoding="utf-8")
                if count_published_text_tokens(staging) == candidate:
                    return candidate
        raise RuntimeError("manifest token accounting cycle has no exact serialization within 16 whitespace pairs and +/-16 tokens; staged render was not published")
    raise RuntimeError("manifest token accounting did not converge within 16 distinct states; staged render was not published")


def _render_weighted(run_dir: Path, store: LedgerStore, ledger: dict) -> dict:
    import shutil

    staging = run_dir / ".render-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    projection = _write_weighted_pages(ledger, staging)
    broken = (
        projection["broken_references"]
        + _broken_markdown_links(staging, check_anchors=True)
        + _unaccounted_media(staging)
    )
    source_tokens = count_frozen_source_tokens(ledger)
    ledger_semantic = count_ledger_semantic_tokens(ledger)
    report = describe_render_budget(source_tokens, 0)
    report["ratio"] = "0.000000"
    pending = projection["pending_group_ids"]
    pending_detail_ids = projection["pending_detail_ids"]
    manifest = {
        "ledger_revision": ledger.get("ledger_revision"),
        "rendered_at": iso(),
        "documentation_policy_version": "weighted-v1",
        "token_budget": report,
        "ledger_semantic_tokens": ledger_semantic["ledger_semantic_tokens"],
        "ledger_semantic_breakdown": {
            "details": ledger_semantic["detail_tokens"],
            "group_body": ledger_semantic["group_body_tokens"],
            "group_evidence": ledger_semantic["group_evidence_tokens"],
        },
        "ledger_semantic_scope": "All Detail behavior and five fact fields, including fragments and historical records; all Group body and extra.evidence_summary. Derived nav_sentence excluded.",
        "ledger_semantic_note": "Ledger prose overlaps published pages; do not add these counts as independent reading cost.",
        "broken_links": broken,
        "page_count": sum(1 for _ in staging.rglob("*.md")),
        "file_page_count": len(projection["file_targets"]),
        "group_page_count": len(projection["group_targets"]),
        "detail_page_count": sum(1 for _ in (staging / "details").glob("*.md")),
        "symbol_count": len((ledger.get("inventory") or {}).get("symbols") or {}),
        "pending_detail_count": len(pending_detail_ids),
        "pending_detail_ids": pending_detail_ids[:20],
        "pending_group_count": len(pending),
        "pending_group_ids": pending[:20],
    }
    published_tokens = _write_counted_manifest(staging, manifest, source_tokens)
    if broken:
        raise ValueError(f"weighted render has {len(broken)} broken links; staged render was not published: {broken[:3]}")
    check_render_budget(source_tokens, published_tokens)

    live = run_dir / "render"
    previous = run_dir / "render.prev"
    if live.exists():
        if previous.exists():
            shutil.rmtree(previous)
        live.rename(previous)
    try:
        staging.rename(live)
    except OSError:
        if previous.exists() and not live.exists():
            previous.rename(live)
        raise

    def bump(current: dict) -> dict:
        fingerprint = projection_fingerprint(current)
        current["render_revision"] = fingerprint
        current["render_content_fingerprint"] = fingerprint
        return current

    store.mutate(bump)
    return manifest


def _broken_markdown_links(root: Path, *, check_anchors: bool = False) -> list[str]:
    broken: list[str] = []
    anchors_by_path: dict[Path, set[str]] = {}

    def anchors(path: Path) -> set[str]:
        cached = anchors_by_path.get(path)
        if cached is not None:
            return cached
        page_anchors: set[str] = set()
        occurrences: dict[str, int] = {}
        for line in _outside_code_lines(path.read_text(encoding="utf-8")):
            page_anchors.update(re.findall(r'<a\s+id=["\']([^"\']+)["\']', line))
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            if heading:
                title = re.sub(r"<[^>]+>", "", heading.group(1)).strip()
                base = _heading_slug(title)
                ordinal = occurrences.get(base, 0)
                page_anchors.add(base if ordinal == 0 else f"{base}-{ordinal}")
                occurrences[base] = ordinal + 1
        anchors_by_path[path] = page_anchors
        return page_anchors

    for path in root.rglob("*.md"):
        for line in _outside_code_lines(path.read_text(encoding="utf-8")):
            for match in _LINK_RE.finditer(line):
                raw = unquote(match.group(1).strip())
                if raw.startswith(("http://", "https://", "mailto:")):
                    continue
                target, _, anchor = raw.partition("#")
                resolved = ((path.parent / target) if target else path).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    broken.append(f"{path.relative_to(root)} -> {raw} (outside render)")
                    continue
                if not resolved.is_file():
                    broken.append(f"{path.relative_to(root)} -> {raw}")
                    continue
                if check_anchors and anchor and anchor not in anchors(resolved):
                    broken.append(f"{path.relative_to(root)} -> {raw} (missing anchor)")
    return broken


def _unaccounted_media(root: Path) -> list[str]:
    unsupported: list[str] = []
    markdown = MarkdownIt("commonmark", {"html": True})

    def has_media(tokens) -> bool:
        for token in tokens:
            if token.type == "image":
                return True
            if token.type in {"html_inline", "html_block"}:
                parser = _MediaParser()
                parser.feed(token.content)
                parser.close()
                if parser.has_media:
                    return True
            if token.children and has_media(token.children):
                return True
        return False

    for path in root.rglob("*.md"):
        if has_media(markdown.parse(path.read_text(encoding="utf-8"))):
            unsupported.append(f"{path.relative_to(root)} -> media embed has no accounted media tokens")
    return unsupported


def _opening_paragraph(ledger: dict, groups: dict, details: dict) -> str:
    repo = ledger.get("repo_root") or ""
    current = {
        group_id: group
        for group_id, group in groups.items()
        if not ((group.get("extra") or {}).get("replaced_by"))
    }
    parentless = [gid for gid, g in current.items() if not g.get("parent_id")]
    root = None
    if len(parentless) == 1 and (current[parentless[0]].get("body") or "").strip():
        root = parentless[0]
    if root is not None:
        return f"Documented tree rooted at `{repo}`.\n\n{current[root]['body'].strip()}"
    if current:
        names = ", ".join(sorted(current)[:5])
        return (
            f"Documented tree rooted at `{repo}`. Imported groups so far: {names}. "
            "Each group page links to member Details."
        )
    return (
        f"Documented tree rooted at `{repo}`. {len(details)} function/module Details are committed. "
        "Architecture groups have not been imported; navigation uses the file tree until then."
    )


def _descendant_details(groups: dict, group_id: str) -> set[str]:
    seen: set[str] = set()
    out: set[str] = set()
    stack = [group_id]
    while stack:
        gid = stack.pop()
        if gid in seen:
            continue
        seen.add(gid)
        group = groups.get(gid) or {}
        out.update(group.get("member_ids") or [])
        stack.extend(group.get("children") or [])
    return out


def _top_groups(groups: dict) -> list[str]:
    current = {
        gid: g
        for gid, g in groups.items()
        if not ((g.get("extra") or {}).get("replaced_by"))
    }
    parentless = sorted(gid for gid, g in current.items() if not g.get("parent_id"))
    if len(parentless) == 1:
        root = parentless[0]
        children = [c for c in (current[root].get("children") or []) if c in current]
        if children:
            return children
    return parentless


def _architecture_section(ledger: dict, groups: dict, names: PageNames) -> list[str]:
    current = {
        gid: g
        for gid, g in groups.items()
        if not ((g.get("extra") or {}).get("replaced_by"))
    }
    if not current:
        return ["(no architecture groups yet)"]
    parentless = [gid for gid, g in current.items() if not g.get("parent_id")]
    lines: list[str] = []
    if len(parentless) == 1:
        root = parentless[0]
        lines.append(f"Root: [{root}]({_group_link(names, root)})")
        lines.append("")
    top = _top_groups(groups)
    for gid in top:
        group = current.get(gid) or {}
        title = group.get("question_answered") or gid
        n_members = len(_descendant_details(groups, gid))
        lines.append(f"- [{title}]({_group_link(names, gid)}) — `{gid}`, {n_members} details")
    lines.append("")
    lines.append(f"All {len(current)} groups are listed flat under 'Semantic groups' below for direct lookup.")
    return lines


def _module_graph_section(ledger: dict, groups: dict, details: dict, names: PageNames) -> list[str]:
    top = _top_groups(groups)
    if not top:
        return ["(module dependency graph appears once architecture groups exist)"]
    membership: dict[str, int] = {}
    for idx, gid in enumerate(top):
        for detail_id in _descendant_details(groups, gid):
            membership.setdefault(detail_id, idx)
    edges = (ledger.get("graph") or {}).get("edges") or []
    counts: dict[tuple[int, int], int] = {}
    for edge in edges:
        a = membership.get(edge.get("subject_id"))
        b = membership.get(edge.get("target_id"))
        if a is None or b is None or a == b:
            continue
        key = (min(a, b), max(a, b))
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return ["(no cross-module edges resolved)"]
    lines = []
    for (a, b), n in sorted(counts.items(), key=lambda item: -item[1]):
        ga, gb = top[a], top[b]
        lines.append(f"- [{ga}]({_group_link(names, ga)}) ↔ [{gb}]({_group_link(names, gb)}) — {n} edges")
    return lines
