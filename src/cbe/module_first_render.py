"""Render a candidate module plan over a frozen CBE inventory.

This projection deliberately keeps structure and explanation separate. Every
canonical symbol has a source locator and a module membership. Every module
title is labelled as a candidate. This projection never turns a legacy
summary into an accepted fact merely because its source revision matches.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any
from cbe.callable_contracts import BOUNDARY, contracts_for, render_contract, reader_references, query_only_syntax, publication_projection

from cbe.render import (
    _broken_markdown_links,
    _compact_label,
    _compact_page,
    _heading_name,
    _heading_slug,
    _relative_target,
    _source_line_numbers,
    _unaccounted_media,
    _write_counted_manifest,
)
from cbe.store import iso
from cbe.static_literals import (
    PROJECTION_VERSION, accepted_numeric_literals, accepted_return_keys,
    compact_literal, compact_return_keys,
)
from cbe.token_budget import (
    check_render_budget,
    count_frozen_source_tokens,
    count_text_tokens,
    describe_render_budget,
)


def _validate_plan(ledger: dict[str, Any], plan: dict[str, Any]) -> dict[str, str]:
    symbols = ((ledger.get("inventory") or {}).get("symbols") or {})
    groups = plan.get("groups") or {}
    if plan.get("source_revision") != ledger.get("source_revision"):
        raise ValueError("module plan source revision differs from frozen inventory")
    if not groups or not isinstance(groups, dict):
        raise ValueError("module plan has no groups")
    group_limit = (ledger.get("documentation_policy") or {}).get("group_limit")
    if type(group_limit) is int and len(groups) > group_limit:
        raise ValueError(f"module plan has {len(groups)} groups beyond group_limit {group_limit}")
    actual: dict[str, str] = {}
    roots: list[str] = []
    for gid, group in groups.items():
        if group.get("group_id") != gid:
            raise ValueError(f"group id mismatch: {gid}")
        parent = group.get("parent_id")
        if parent is None:
            roots.append(gid)
        elif parent not in groups or gid not in (groups[parent].get("children") or []):
            raise ValueError(f"group parent edge is broken: {gid}")
        if not str(group.get("question_answered") or "").strip():
            raise ValueError(f"group has no reader question: {gid}")
        if (group.get("extra") or {}).get("review_state") != "candidate" or str(group.get("body") or "").strip():
            raise ValueError(f"candidate renderer cannot publish unverified group prose: {gid}")
        for sid in group.get("member_ids") or []:
            if sid not in symbols or sid in actual:
                raise ValueError(f"unknown or multiply assigned symbol: {sid}")
            actual[sid] = gid
        for child in group.get("children") or []:
            if child not in groups or groups[child].get("parent_id") != gid:
                raise ValueError(f"group child edge is broken: {gid} -> {child}")
    if len(roots) != 1 or set(actual) != set(symbols):
        raise ValueError("module plan requires one root and complete unique symbol ownership")
    if "symbol_to_module" in plan and plan["symbol_to_module"] != actual:
        raise ValueError("module plan has conflicting legacy symbol_to_module mapping")
    visited: set[str] = set()
    pending = [roots[0]]
    while pending:
        gid = pending.pop()
        if gid in visited:
            raise ValueError(f"module plan repeats a group in its tree: {gid}")
        visited.add(gid)
        pending.extend(groups[gid].get("children") or [])
    if visited != set(groups):
        raise ValueError("module plan contains unreachable groups")
    return actual


def _page_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _prose(value: Any) -> str:
    """Model-sourced prose embedded in pages: escape link-forming brackets.

    Behavior text legitimately contains code notation like ``typemap[type_](value)``.
    Unescaped, markdown reads ``[...](...)`` as a link whose target is not a page,
    which the broken-link gate (correctly) rejects. Escaping keeps the notation
    visible as literal text without changing the stored record.
    """
    return str(value).replace("[", "\\[").replace("]", "\\]")


def fact_projection_hash(ledger: dict[str, Any]) -> str:
    """Fingerprint every fact currently visible through pages or query."""
    visible = {}
    reviews = ledger.get("fact_reviews") or {}
    for sid, detail in (ledger.get("details") or {}).items():
        review = reviews.get(sid) or {}
        if not isinstance(detail, dict) or review.get("state") not in {"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"}:
            continue
        digest = hashlib.sha256(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        if review.get("content_sha256") == digest:
            visible[sid] = {"record": detail, "state": review["state"]}
    return hashlib.sha256(json.dumps(
        {"facts": visible, "literal_projection_version": PROJECTION_VERSION,
         "source_literals": accepted_numeric_literals(ledger),
         "return_keys": accepted_return_keys(ledger)},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def _group_label(group: dict[str, Any]) -> str:
    """Use the brief candidate name for navigation; keep the full question on its page."""
    return str(group.get("title") or group["group_id"]).replace("-", " ")[:96]


def _fact_digest(detail: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def explained_symbols(ledger: dict[str, Any]) -> dict[str, str]:
    """Symbols with a hash-bound fact -> review mark S/B or syntax mark Y."""
    details = ledger.get("details") or {}
    reviews = ledger.get("fact_reviews") or {}
    explained: dict[str, str] = {}
    for sid, detail in details.items():
        if not isinstance(detail, dict):
            continue
        review = reviews.get(sid) or {}
        state = review.get("state") if review.get("content_sha256") == _fact_digest(detail) else None
        if state == "source_checked":
            explained[sid] = "S"
        elif state == "batch_accepted":
            explained[sid] = "B"
        elif state == "syntax_evidenced":
            explained[sid] = "Y"
        elif state == "mechanically_validated":
            explained[sid] = "M"
    return explained


def file_page_anchors(
    symbols: dict[str, Any], by_file: dict[str, list[str]], explained: dict[str, str],
    previous: dict[str, str] | None = None,
) -> dict[str, str]:
    """One compact source locator per object, independent of review state.

    Existing published targets have priority; fresh names need no repeated long
    hash marker. Review state belongs to the row/legend, never the anchor.
    """
    anchors: dict[str, str] = {}
    for path, ids in by_file.items():
        ids.sort(key=lambda sid: ((symbols[sid].get("span") or {}).get("start") or 0, sid))
        occurrences: dict[str, int] = {}
        for sid in ids:
            if previous and previous.get(sid):
                anchors[sid] = previous[sid]
        used = set(anchors[sid] for sid in ids if sid in anchors)
        for sid in ids:
            if sid not in explained or sid in anchors:
                continue
            base = _heading_slug(_heading_name(str(symbols[sid].get("name") or sid)))
            ordinal = occurrences.get(base, 0)
            candidate = base if ordinal == 0 else f"{base}-{ordinal}"
            while candidate in used:
                ordinal += 1
                candidate = f"{base}-{ordinal}"
            anchors[sid] = candidate
            used.add(candidate)
            occurrences[base] = ordinal + 1
        for sid in ids:
            if sid not in anchors:
                base = _heading_slug(_heading_name(str(symbols[sid].get("name") or sid)))
                ordinal = 0
                candidate = base
                while candidate in used:
                    ordinal += 1
                    candidate = f"{base}-{ordinal}"
                anchors[sid] = candidate
                used.add(candidate)
    return anchors


def _previous_anchors(ledger: dict) -> dict[str, str]:
    diagnostics = ledger.get("reader_render_diagnostics") or {}
    if diagnostics.get("source_revision") != ledger["source_revision"]:
        return {}
    accounting = diagnostics.get("syntax_projection_accounting") or {}
    targets = accounting.get("symbol_targets") or {
        sid: row.get("target") for sid, row in (accounting.get("contracts") or {}).items()}
    return {sid: target.partition("#")[2] for sid, target in targets.items()
            if isinstance(target, str) and "#" in target}


def _tests_importing_source(inventory: dict[str, Any]) -> dict[str, set[str]]:
    """Cross-link only exact frozen import statements, without claiming test coverage."""
    files = inventory["files"]
    module_files: dict[str, str] = {}
    for path in files:
        if not path.endswith(".py") or path.startswith(("t/", "tests/")):
            continue
        dotted = path[:-3].replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        module_files[dotted] = path
    result: dict[str, set[str]] = defaultdict(set)
    for relation in inventory.get("relations") or []:
        test_path = relation.get("path")
        if relation.get("kind") != "import" or not isinstance(test_path, str):
            continue
        if not test_path.startswith(("t/", "tests/")) or test_path not in files:
            continue
        imported = (relation.get("extra") or {}).get("module")
        source_path = module_files.get(imported)
        if source_path:
            result[source_path].add(test_path)
    return result


def render_module_plan(
    ledger: dict[str, Any],
    plan: dict[str, Any],
    output_dir: Path,
    explanations_package: dict[str, Any] | None = None,
    *,
    run_dir: Path,
    plan_path: Path | None = None,
) -> dict[str, Any]:
    """Stage, account, validate and publish a compact module-first projection.

    ``output_dir`` is the reader-visible render directory. Frozen source files
    are never overwritten. Structural catalogue coverage is reported separately from
    the number of reviewed module explanations.
    """

    assignments = _validate_plan(ledger, plan)
    if explanations_package is None:
        explanations: dict[str, dict[str, Any]] = {}
    else:
        from cbe.module_explanations import validate_module_explanations

        explanations = validate_module_explanations(ledger, plan, explanations_package)
    requested_output = Path(output_dir).absolute()
    if requested_output.is_symlink():
        raise ValueError("module render output cannot be a symlink")
    output_dir = requested_output.resolve()
    repo = Path(ledger["repo_root"]).resolve()
    run_dir = Path(run_dir).resolve()
    plan_path = Path(plan_path or run_dir / "module_plan.json").resolve()
    protected = {
        "semantic_ledger.json", "semantic_ledger.json.prev",
        "semantic_ledger.json.lock", "commit_receipt.json",
        "module_plan.json", "module_explanations.json", "status.json",
        "packets", "prompts", "raw", "reviews", "provider",
        "provider-receipts",
    }
    # The requested output is the only pre-existing path the publisher swaps.
    # Stage and backup directories are created with unique names below, so a
    # sibling named reader.staging or reader.prev remains entirely untouched.
    for target in (output_dir,):
        if target.is_symlink():
            raise ValueError("module render publish path cannot be a symlink")
        target = target.resolve()
        if target == repo or any(
            (repo / relative).resolve().is_relative_to(target)
            for relative, record in (ledger.get("inventory") or {}).get("files", {}).items()
            if record.get("enrolled", True)
        ):
            raise ValueError("module render publish path would replace frozen source files")
        if run_dir.is_relative_to(target):
            raise ValueError("module render publish path would replace the run directory")
        if target.is_relative_to(run_dir):
            relative = target.relative_to(run_dir)
            if relative.parts and relative.parts[0] in protected:
                raise ValueError("module render publish path would replace run machine state")
    source_tokens = count_frozen_source_tokens(ledger)
    inventory = ledger["inventory"]
    symbols = inventory["symbols"]
    callable_syntax = contracts_for(ledger)
    syntax_references = reader_references(ledger)
    details = ledger.get("details") or {}
    fact_reviews = ledger.get("fact_reviews") or {}
    files = inventory["files"]
    groups = plan["groups"]
    policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))

    file_pages = {path: _compact_page("files", path) for path in files}
    group_pages = {gid: _compact_page("groups", gid) for gid in groups}
    test_imports = _tests_importing_source(inventory)
    catalogue_module_ids = [gid for gid, group in groups.items() if group.get("member_ids")]
    lines = _source_line_numbers(ledger, symbols)
    by_file: dict[str, list[str]] = defaultdict(list)
    for sid, symbol in symbols.items():
        by_file[symbol["path"]].append(sid)
    # Once every member-bearing group has a reviewed page, structural ancestor
    # pages only repeat navigation that INDEX and those module pages provide.
    # Keep the full candidate tree while any member group is still pending.
    pending_member_groups = any(
        group.get("member_ids") and gid not in explanations
        for gid, group in groups.items()
    )
    rendered_group_ids = (
        set(groups) if pending_member_groups else set(explanations)
    )
    # Each accepted module page links its first ten source files. For a small
    # complete tree those links already cover the catalogue, so FILES would
    # duplicate the same list. Larger or pending trees retain FILES.
    accepted_file_paths = {
        symbols[sid]["path"]
        for gid in explanations for sid in groups[gid].get("member_ids") or []
    }
    emit_file_index = not (
        files and len(files) <= 10 and not pending_member_groups
        and set(files) <= accepted_file_paths
    )
    explained = explained_symbols(ledger)
    source_literals = accepted_numeric_literals(ledger)
    declaration_targets = {
        (record["path"], record["name"], record["line"]):
        file_pages[record["path"]] + "#decl-" + hashlib.sha256(
            json.dumps([record["path"], record["name"], record["line"]]).encode()).hexdigest()[:16]
        for records in source_literals.values() for record in records
    }
    return_keys = accepted_return_keys(ledger)
    previous_anchors = _previous_anchors(ledger)
    if (ledger.get("reader_render_diagnostics") or {}).get("source_revision") == ledger["source_revision"]:
        # Old initial renders predated the internal target map. Preserve only
        # an exact canonical hash marker actually present in that same-revision
        # output, rather than imposing legacy marker cost on every fresh run.
        for path, ids in by_file.items():
            old_page = output_dir / file_pages[path]
            if old_page.is_file():
                old_text = old_page.read_text(encoding="utf-8")
                for sid in ids:
                    legacy = "syntax-" + hashlib.sha256(sid.encode()).hexdigest()[:16]
                    if f'id="{legacy}"' in old_text:
                        previous_anchors.setdefault(sid, legacy)
    anchors = file_page_anchors(symbols, by_file, explained, previous_anchors)
    symbol_targets = {
        sid: (
            f"{file_pages[symbols[sid]['path']]}#{anchors[sid]}"
            if sid in anchors else file_pages[symbols[sid]["path"]]
        )
        for sid in symbols
    }

    def heading(sid: str) -> str:
        name = _heading_name(str(symbols[sid].get("name") or sid))
        # Using the actual locator as the heading disambiguates duplicate names
        # without a second long HTML marker or review-dependent GFM numbering.
        return name if _heading_slug(name) == anchors[sid] else anchors[sid]

    def declaration_name(sid: str) -> str | None:
        name = str(symbols[sid].get("name") or "")
        return name if heading(sid) == _heading_name(name) else None

    def link(from_page: str, to_page: str, label: str) -> str:
        target_page, sep, anchor = to_page.partition("#")
        target = "#" + anchor if sep and target_page == from_page else _relative_target(from_page, to_page)
        return f"[{_compact_label(label)}]({target})"

    published_reference_ids: set[str] = set()
    def reference_profile(ref: dict) -> tuple:
        reason = str(ref.get("reason") or "")
        target_name = str(symbols[ref["target_id"]].get("name") or "")
        # This is a reversible program-generated reason, not semantic prose
        # deduplication. Its named target remains at the stable link destination.
        if reason == "call " + target_name:
            reason = "call <target name>"
        return (ref["kind"], ref["status"], ref["method"], ref["confidence"], reason)

    def reference_lines(sid: str, page: str, path: str, profiles: dict) -> list[str]:
        refs = syntax_references.get(sid) or {}
        links = [link(page, symbol_targets[ref["target_id"]],
                      (f"L{lines[ref['target_id']]}" if symbols[ref["target_id"]]["path"] == path
                       else str(symbols[ref["target_id"]].get("name"))) +
                      f" [{profiles[reference_profile(ref)]}]")
                 for ref in refs.get("callees", [])]
        rows = ["Refs: " + ", ".join(dict.fromkeys(links))] if links else []
        for ref in refs.get("declarations", []):
            label = ref["name"] if ref["source_path"] == path else f"{ref['name']} · {ref['source_path']}:L{ref['line']}"
            target = declaration_targets.get((ref["source_path"], ref["name"], ref["line"]))
            rows.append("Uses: " + (link(page, target, label) if target else
                                      _prose(label + f" L{ref['line']}")))
        published_reference_ids.add(sid)
        return rows

    if emit_file_index:
        file_index = [
            "# Source files", "",
            "`[S]` source-checked; `[B]` batch-accepted; `[Y]` syntax-only; `[M]` mechanically validated, narrative semantics unverified. `[literal]` and `[return keys]` show frozen syntax, not every runtime path; omission does not mean absence. See [CLI navigation](INDEX.md#cli-navigation) for module-members, query and resolve.",
        ]
        for path in sorted(files):
            file_index.append(f"- {link('FILES.md', file_pages[path], path)}")
        _page_lines(staging / "FILES.md", file_index)

    for path in sorted(files):
        page = file_pages[path]
        file_module_ids = sorted({assignments[sid] for sid in by_file[path]})
        content: list[str] = [f"# `{path}`", ""]
        if file_module_ids:
            content += ["Modules: " + ", ".join(link(page, group_pages[gid], gid) for gid in file_module_ids)]
        profiles = sorted({reference_profile(ref)
                           for sid in by_file[path] for ref in syntax_references.get(sid, {}).get("callees", [])}, key=repr)
        profile_ids = {profile: f"r{i + 1}" for i, profile in enumerate(profiles)}
        if any(sid in callable_syntax for sid in by_file[path]):
            content += ["", "Code blocks: declaration syntax only; runtime contracts are unknown. "
                        + link(page, "INDEX.md#cli-navigation", "Syntax boundary") + "."]
        if any(sid not in explained for sid in by_file[path]):
            content += ["Unlabelled L entries: declaration/reference syntax; behavior unreviewed."]
        if profiles or any(syntax_references.get(sid, {}).get("declarations") for sid in by_file[path]):
            content += ["Refs: static candidates/name references; runtime binding unknown."]
        if profiles:
            content.append("Call-site path/range: unspecified unless shown; target links locate declarations.")
        if profiles:
            content.append("; ".join(f"{profile_ids[p]}={p[0]}/{p[1]}/{p[2]}/{p[3]}" +
                                     (" · " + _prose(p[4]) if p[4] else "") for p in profiles))
            if any(p[4] == "call <target name>" for p in profiles):
                content.append("<target name> is the linked declaration's name.")
        explained_ids = [sid for sid in by_file[path] if sid in explained]
        rendered_literals: dict[str, str] = {}
        if explained_ids:
            content += ["", "`[S]` source · `[B]` batch · `[Y]` syntax · `[M]` mechanical, narrative semantics unverified."]
            for sid in explained_ids:
                symbol = symbols[sid]
                content += [
                    "", f"### {heading(sid)}",
                ]
                if sid in callable_syntax:
                    content += [render_contract(callable_syntax[sid], declaration_name(sid))]
                content.extend(reference_lines(sid, page, path, profile_ids))
                behavior = details[sid]["behavior"]
                if symbol["kind"] == "module_residual" and behavior.startswith(
                    "Program syntax evidence: module residual contains only docstring literals, import statements, literal assignments."):
                    behavior = "Module syntax: docstrings, imports and literal bindings. See INDEX syntax boundary."
                content.append(f"L{lines[sid]} [{explained[sid]}]: {_prose(behavior)}")
                from cbe.syntax_facts import atoms_for
                statement_facts = atoms_for(ledger, sid)
                for atom in statement_facts["atoms"]:
                    if atom["kind"] in {"return_none", "raise_expression", "reraise", "update", "append_call"} or atom["guards"]:
                        guards = " / ".join(atom["guards"])
                        content.append(f"[atom] L{atom['line']}: " + ("`" + guards + "` → " if guards else "") + "`" + atom["syntax"] + "`")
                if statement_facts.get("omitted_atom_count"):
                    content.append(f"[atom] {statement_facts['omitted_atom_count']} additional statements omitted; extraction partial.")
                from cbe.behavior_contracts import accepted_projection, claim_text
                behavioral = accepted_projection(ledger, sid)
                for claim in behavioral.get("claims") or []:
                    anchor = "claim-" + hashlib.sha256((sid + ":" + claim["id"]).encode()).hexdigest()[:16]
                    content.append(f'<a id="{anchor}"></a>')
                    content.append(_prose(claim_text(claim)))
                for ref in behavioral.get("claim_refs") or []:
                    anchor = "claim-" + hashlib.sha256((ref["symbol_id"] + ":" + ref["claim_id"]).encode()).hexdigest()[:16]
                    target = symbol_targets.get(ref["symbol_id"])
                    if ref["status"] == "accepted" and target:
                        target_page = target.split("#", 1)[0]
                        content.append("Rule: " + link(file_pages[path], target_page + "#" + anchor, ref["claim_id"]))
                    else:
                        content.append("Unresolved rule: " + _prose(ref["claim_id"]))
                for gap in behavioral.get("local_view_gaps") or []:
                    target = symbol_targets.get(gap["dependency_id"])
                    locator = link(file_pages[path], target, "dependency") if target else "dependency"
                    status = "accepted dependency available; relation requires review" if gap["accepted_dependency_available"] else "dependency unresolved"
                    content.append(_prose(gap["reason"]) + " (" + locator + "; " + status + ").")
                for unknown in behavioral.get("current_unresolved") or []:
                    content.append("Unknown: " + _prose(str(unknown)))
                for item in source_literals.get(sid, []):
                    target = declaration_targets[(item["path"], item["name"], item["line"])]
                    value = compact_literal(item)
                    if target in rendered_literals:
                        if rendered_literals[target] != value:
                            raise ValueError("same frozen declaration has conflicting literal projections")
                        continue
                    rendered_literals[target] = value
                    content += [f'<a id="{target.partition("#")[2]}"></a>', value]
                if sid in return_keys:
                    content.append(compact_return_keys(return_keys[sid]))
        for sid in by_file[path]:
            if sid not in explained:
                content += ["", f"### {heading(sid)}", f"L{lines[sid]}"]
                if sid in callable_syntax:
                    content.append(render_contract(callable_syntax[sid], declaration_name(sid)))
                content.extend(reference_lines(sid, page, path, profile_ids))
        _page_lines(staging / page, content)

    for gid, group in groups.items():
        if gid not in rendered_group_ids:
            continue
        page = group_pages[gid]
        title = str(group.get("question_answered") or gid)
        content = [f"# {_compact_label(title)}", ""]
        explanation = explanations.get(gid)
        if explanation is None:
            content.append("> Candidate source grouping; no independently reviewed behavior explanation is published.")
        else:
            grade = "Mechanically validated module explanation; narrative semantics unverified" if explanations[gid]["review"].get("decision") == "mechanically_validated" else "Independently reviewed module explanation"
            content.append(f"> {grade}. Query this module ID for source references and validation metadata.")
            content += ["", "## Purpose", _prose(explanation["summary"]), "", "## Execution and dependencies", _prose(explanation["flow"])]
            if explanation["uncertainties"]:
                content += ["", "## Unresolved", _prose(explanation["uncertainties"])]
            content += ["", "## Key source entries"]
            for sid in explanation["key_symbols"][:3]:
                symbol = symbols[sid]
                label = f"{symbol.get('name') or sid} · {symbol['path']}:L{lines[sid]}"
                content.append(f"- {link(page, symbol_targets[sid], label)}")
        children = [child for child in group.get("children") or []
                    if child in rendered_group_ids]
        if children:
            content += ["", "## Modules"]
            content.extend(
                f"- {link(page, group_pages[child], _group_label(groups[child]))}"
                for child in children
            )
        members = group.get("member_ids") or []
        if members:
            content += ["", f"## Source entry ({len(members)} symbols)"]
            ranked = sorted(
                members,
                key=lambda sid: (
                    symbols[sid]["path"].startswith(("t/", "tests/")),
                    -int((policy.get(sid) or {}).get("score") or 0),
                    sid,
                ),
            )
            content.append(f"{link(page, 'INDEX.md#cli-navigation', 'module-members')}: `{gid}`.")
            source_paths = sorted({symbols[sid]["path"] for sid in members})
            content += ["", f"## Source files ({len(source_paths)})"]
            for source_path in source_paths[:10]:
                content.append(f"- {link(page, file_pages[source_path], source_path)}")
            if len(source_paths) > 10:
                content.append(f"- {link(page, 'FILES.md', 'Browse all source files')}")
            if gid != "test-support-catalogue":
                related_tests = sorted({
                    test_path for source_path in source_paths
                    for test_path in test_imports.get(source_path, set())
                })
                if related_tests:
                    content += ["", f"## Tests importing these sources ({len(related_tests)})"]
                    for test_path in related_tests[:8]:
                        content.append(f"- {link(page, file_pages[test_path], test_path)}")
                    if len(related_tests) > 8:
                        content.append(f"- {len(related_tests) - 8} more; inspect frozen import relations for the full list")
        _page_lines(staging / page, content)

    roots = [gid for gid, group in groups.items() if group.get("parent_id") is None]
    root_id = roots[0]
    index = ["# Codebase Explorer · module-first map", "", f"> {len(explanations)} published module explanations; individual validation grades are shown on their pages. Other groups are structural candidates. All {len(symbols)} symbols have published documentation targets."]
    from cbe.review_policy import summary as review_summary
    policy = review_summary(ledger)
    index += ["", f"> Semantic review mode: {policy['mode']}. {policy['mechanical_boundary']}"]
    index += ["", "## CLI navigation", ""]
    index += ["[syntax] " + BOUNDARY + " Imports may execute code; literal bindings and return annotations are not runtime guarantees."]
    from cbe.syntax_facts import BOUNDARY as STATEMENT_BOUNDARY, reader_facts
    index += ["[atom] Python only: " + STATEMENT_BOUNDARY]
    index += ["Python parameter tails combine with the heading as `def NAME...` (async shown); other heads are complete. Refs are static candidates; runtime binding is unknown."]
    if symbols:
        example_gid = next(iter(explanations), None) or next(gid for gid in groups if groups[gid].get('member_ids'))
        example_sid = groups[example_gid]['member_ids'][0]
        run_assignment = (f"RUN={shlex.quote('./' + run_dir.relative_to(repo).as_posix())}"
                          if run_dir.is_relative_to(repo)
                          else 'RUN="${CBE_RUN_DIR}"')
        if Path(plan_path) == run_dir / "module_plan.json":
            plan_assignment = 'PLAN="$RUN/module_plan.json"'
        elif Path(plan_path).is_relative_to(repo):
            plan_assignment = f"PLAN={shlex.quote('./' + Path(plan_path).relative_to(repo).as_posix())}"
        else:
            plan_assignment = 'PLAN="${CBE_PLAN_PATH}"'
        index += ["module-members lists exact IDs; repeat next_offset until null. Query module/symbol records; resolve symbol documentation URLs.",
                  "Run these commands from the repository root. For externally stored runs, set `CBE_RUN_DIR` (and `CBE_PLAN_PATH` for an external custom plan) to their local paths first.",
                  "```sh", run_assignment, plan_assignment,
                  f"GROUP={shlex.quote(example_gid)}", f"ID={shlex.quote(example_sid)}",
                  'cbe module-members --run-dir "$RUN" --plan "$PLAN" --group-id "$GROUP" --offset 0 --limit 100',
                  'cbe query --run-dir "$RUN" --id "$GROUP"',
                  'cbe query --run-dir "$RUN" --id "$ID"',
                  'cbe resolve --run-dir "$RUN" --id "$ID"', "```"]
    else:
        index += ["No symbol or module-member targets are present in this empty scope."]
    if emit_file_index:
        index += ["", link("INDEX.md", "FILES.md", f"Browse all {len(files)} source files")]
    else:
        index += ["", "`[S]` source-checked; `[B]` batch-accepted; `[Y]` syntax-only; `[M]` mechanically validated, narrative semantics unverified. `[literal]`/`[return keys]` are frozen syntax, not every runtime path."]
    from cbe.system_workflow import accepted_system
    system = accepted_system(ledger)
    if system is not None:
        grade = "mechanically validated; narrative semantics unverified" if system["review"].get("decision") == "mechanically_validated" else "independently reviewed"
        index += ["", f"## System overview ({grade})", "",
                  _prose(system["overview"]), "",
                  f"- Entry points: {_prose(system['entry_points'])}",
                  f"- Lifecycle: {_prose(system['lifecycle'])}",
                  f"- Data flow: {_prose(system['data_flow'])}"]
        if system.get("uncertainties"):
            index += ["", f"Open uncertainties: {_prose(system['uncertainties'])}"]
    functional_areas = [gid for gid in groups[root_id].get("children") or []
                        if gid in rendered_group_ids]
    if functional_areas:
        index += ["", "## Functional areas"]
        for gid in functional_areas:
            index.append(f"- {link('INDEX.md', group_pages[gid], _group_label(groups[gid]))}")
    if explanations:
        index += ["", "## Published modules"]
        ranked_modules = sorted(explanations, key=lambda gid: (-len(groups[gid].get("member_ids") or []), gid))
        for gid in ranked_modules:
            explanation = explanations[gid]
            index.append(f"- {link('INDEX.md', group_pages[gid], _group_label(groups[gid]))}")
        primary = explanations[ranked_modules[0]]
        if primary.get("key_symbols"):
            sid = primary["key_symbols"][0]
            index += ["", "Start with " + link("INDEX.md", symbol_targets[sid],
                      str(symbols[sid].get("name") or sid)) + "."]
        if primary.get("uncertainties"):
            index += ["", "Boundary: " + link("INDEX.md", group_pages[ranked_modules[0]] + "#unresolved", "Module uncertainties")]
    _page_lines(staging / "INDEX.md", index)

    broken = _broken_markdown_links(staging, check_anchors=True) + _unaccounted_media(staging)
    plan_hash = hashlib.sha256(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    budget = describe_render_budget(source_tokens, 0)
    budget["ratio"] = "0.000000"
    query_only_tokens = 0
    syntax_accounting = {"version": "published-declaration-equivalence/1", "symbol_targets": symbol_targets, "contracts": {},
                         "references": {}, "syntax_query_only_tokens": 0,
                         "reference_query_only_tokens": 0}
    for sid, value in callable_syntax.items():
        page = file_pages[symbols[sid]["path"]]
        representation = value.get("compact_header", value.get("header", ""))
        projection = publication_projection(value, declaration_name(sid))
        published = value["status"] == "complete" and render_contract(value, declaration_name(sid)) in (staging / page).read_text() and (
            representation == value["header"] or value.get("compact_header_verified") is True)
        delta = query_only_syntax(value, published=published)
        tokens = count_text_tokens(json.dumps(delta, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"))) if delta else 0
        syntax_accounting["syntax_query_only_tokens"] += tokens
        syntax_accounting["contracts"][sid] = {"content_hash": value["content_hash"],
            "target": symbol_targets[sid], "header_sha256": hashlib.sha256(value.get("header", "").encode()).hexdigest(),
            "published_header_sha256": hashlib.sha256(representation.encode()).hexdigest(),
            "signature_ast_sha256": value.get("signature_ast_sha256"),
            "representation": "ast_equivalent" if representation != value.get("header") else "raw",
            "display_projection": projection["representation"], "heading_name": declaration_name(sid),
            "structured_from_published_header": published, "query_only_fields": list(delta),
            "query_only_tokens": tokens}
    for sid, value in syntax_references.items():
        # For published syntax, names/kinds/status/method/confidence and declaration
        # locators are shown. Exact call expression character ranges are query-only.
        delta = ({"callee_source_ranges": [
            {"target_id": ref["target_id"], "source_path": ref["source_path"], "source_span": ref["source_span"]}
            for ref in value["callees"]
            if ref.get("source_path") is not None or ref.get("source_span") is not None
        ]} if sid in published_reference_ids else value)
        reasons = [ref["reason"] for ref in value.get("callees", []) if ref.get("reason")]
        if reasons and sid not in published_reference_ids:
            delta["reference_reasons"] = reasons
        if delta == {"callee_source_ranges": []}:
            delta = {}
        tokens = count_text_tokens(json.dumps(delta, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"))) if delta else 0
        syntax_accounting["reference_query_only_tokens"] += tokens
        syntax_accounting["references"][sid] = {"target": symbol_targets[sid],
            "locators_published": sid in published_reference_ids,
            "null_call_site_authority": "file Refs legend" if sid in published_reference_ids else None,
            "query_only_fields": list(delta), "query_only_tokens": tokens}
    query_only_tokens += syntax_accounting["syntax_query_only_tokens"] + syntax_accounting["reference_query_only_tokens"]
    statement_query_tokens = 0
    for sid in symbols:
        facts = reader_facts(ledger, sid)
        if not facts:
            continue
        delta = {key: value for key, value in facts.items() if key != "atoms"}
        delta["atoms"] = [{key: value for key, value in atom.items() if key in {"id", "kind"}}
            if sid in explained and (atom["kind"] in {"return_none", "raise_expression", "reraise", "update", "append_call"} or atom["guards"]) else atom
            for atom in facts["atoms"]]
        statement_query_tokens += count_text_tokens(json.dumps(delta, sort_keys=True, separators=(",", ":")))
    syntax_accounting["statement_query_only_tokens"] = statement_query_tokens
    query_only_tokens += statement_query_tokens
    for sid, detail in details.items():
        review = fact_reviews.get(sid) or {}
        if not isinstance(detail, dict) or review.get("state") not in {"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"}:
            continue
        digest = hashlib.sha256(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        if review.get("content_sha256") != digest:
            continue
        for field in ("inputs_outputs", "effects", "failures", "dependencies", "unresolved"):
            value = detail.get(field)
            if value in (None, "", [], {}):
                continue
            rendered = value if isinstance(value, str) else json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            query_only_tokens += count_text_tokens(rendered)
    budget["query_only_tokens"] = query_only_tokens
    budget["effective_document_tokens"] = -1
    budget["effective_ratio"] = "pending"
    budget["policy"] = (
        "strict" if (ledger.get("documentation_policy") or {}).get("budget_mode") != "report"
        else "report"
    )
    budget["target_status"] = "pending"
    manifest = {
        "documentation_policy_version": "module-first-v2-candidate",
        "source_revision": ledger["source_revision"],
        "plan_sha256": plan_hash,
        "facts_sha256": fact_projection_hash(ledger),
        "explanations_sha256": hashlib.sha256(json.dumps(explanations_package or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "rendered_at": iso(),
        "token_budget": budget,
        "symbol_catalogue_count": len(symbols),
        "module_membership_count": len(assignments),
        "module_count": len(catalogue_module_ids),
        "group_page_count": len(rendered_group_ids),
        "accepted_group_explanation_count": len(explanations),
        "candidate_group_count": len(groups) - len(explanations),
        "individually_explained_count": sum(
            isinstance(details.get(sid), dict)
            and (fact_reviews.get(sid) or {}).get("state") == "source_checked"
            and (fact_reviews.get(sid) or {}).get("content_sha256") == hashlib.sha256(json.dumps(
                details[sid], ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest()
            for sid in symbols
            if symbols[sid]["kind"] in {"function", "method", "lambda"}
        ),
        "file_page_count": len(file_pages),
        "member_page_count": 0,
        "page_count": sum(1 for _ in staging.rglob("*.md")),
        "broken_links": broken,
        "syntax_projection_accounting": syntax_accounting,
    }
    # Keep operational hashes and redundant page diagnostics in the run ledger.
    # The reader manifest contains only fields needed to judge this publication.
    reader_manifest = {key: manifest[key] for key in (
        "documentation_policy_version", "source_revision", "token_budget",
        "symbol_catalogue_count", "accepted_group_explanation_count", "broken_links",
    )}
    published_tokens = _write_counted_manifest(staging, reader_manifest, source_tokens)
    if broken:
        raise ValueError(f"module plan render has {len(broken)} broken links; candidate was not published: {broken[:3]}")
    check_render_budget(
        source_tokens, published_tokens + query_only_tokens,
        strict=(ledger.get("documentation_policy") or {}).get("budget_mode") != "report",
    )
    backup_parent = None
    if output_dir.exists():
        backup_parent = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.prev-", dir=output_dir.parent))
        output_dir.rename(backup_parent / output_dir.name)
    try:
        staging.rename(output_dir)
    except OSError:
        if backup_parent is not None and not output_dir.exists():
            (backup_parent / output_dir.name).rename(output_dir)
        raise
    if backup_parent is not None:
        shutil.rmtree(backup_parent)
    return manifest


def page_module_members(
    ledger: dict[str, Any],
    plan: dict[str, Any],
    group_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Fetch exact module ownership on demand instead of publishing 9k links."""
    _validate_plan(ledger, plan)
    if group_id not in plan["groups"]:
        raise ValueError(f"unknown module group: {group_id}")
    if offset < 0 or not 1 <= limit <= 500:
        raise ValueError("offset must be nonnegative and limit between 1 and 500")
    ids = list(plan["groups"][group_id].get("member_ids") or [])
    selected = ids[offset : offset + limit]
    callable_syntax = contracts_for(ledger, selected)
    from cbe.syntax_facts import reader_facts
    syntax_references = reader_references(ledger, selected)
    symbols = ledger["inventory"]["symbols"]
    details = ledger.get("details") or {}
    reviews = ledger.get("fact_reviews") or {}
    line_numbers = _source_line_numbers(ledger, {sid: symbols[sid] for sid in selected})

    def fact_state(sid: str) -> str:
        detail = details.get(sid)
        review = reviews.get(sid) or {}
        if not isinstance(detail, dict):
            return "catalogued"
        digest = hashlib.sha256(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return review.get("state", "author_fact") if review.get("content_sha256") == digest else "catalogued"

    return {
        "group_id": group_id,
        "total": len(ids),
        "offset": offset,
        "next_offset": offset + len(selected) if offset + len(selected) < len(ids) else None,
        "items": [
            {
                "symbol_id": sid,
                **({"callable_syntax": callable_syntax[sid]} if sid in callable_syntax else {}),
                **({"syntax_references": syntax_references[sid]} if sid in syntax_references else {}),
                **({"syntax_facts": facts} if (facts := reader_facts(ledger, sid)) else {}),
                "name": symbols[sid].get("name"),
                "kind": symbols[sid].get("kind"),
                "source_path": symbols[sid]["path"],
                "source_line": line_numbers[sid],
                "tier_signal": ((ledger.get("documentation_policy") or {}).get("symbols") or {}).get(sid, {}).get("tier"),
                "explanation_state": fact_state(sid),
            }
            for sid in selected
        ],
    }


def resolve_module_reader_target(
    ledger: dict[str, Any], plan: dict[str, Any], symbol_id: str
) -> str:
    """Resolve one canonical symbol to its published reader target.

    Explained symbols resolve to their file-page heading anchor; locator-only
    symbols resolve to the file page itself (their dense index line carries
    the structural position).
    """
    _validate_plan(ledger, plan)
    symbols = ledger["inventory"]["symbols"]
    if symbol_id not in symbols:
        raise ValueError(f"unknown canonical symbol: {symbol_id}")
    path = symbols[symbol_id]["path"]
    by_file: dict[str, list[str]] = defaultdict(list)
    for sid, symbol in symbols.items():
        by_file[symbol["path"]].append(sid)
    anchors = file_page_anchors(symbols, by_file, explained_symbols(ledger), _previous_anchors(ledger))
    page = _compact_page("files", path)
    if symbol_id in anchors:
        return f"{page}#{anchors[symbol_id]}"
    return page
