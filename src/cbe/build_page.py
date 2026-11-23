"""The optional "How to build and integrate" page (``--build-page``): inputs, task, check, page.

Off by default; a run without it plans, reads and renders exactly as before. With it, the
plan reads the README, a bounded part of ``docs/`` and the build manifests (never source),
freezes that text in the run, and queues one ``build`` task. The model writes short points on
installing, building, testing, packaging, integrating and migrating; every point cites line
ranges of the files it was shown, and the program checks each citation. The program, not the
model, reads the manifest facts (name, version, scripts, targets) for the top of the page.
"""
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from cbe.grammars import DEFAULT_EXCLUDE_DIR_NAMES
from cbe.token_budget import count_text_tokens

DEFAULT_TOKENS = 24_000          # numbered input text the build task may read
MANIFEST_TOKENS = 4_000          # one manifest is cut here (a long pom.xml, a long Makefile)
ANSWER_TOKENS = 1_800            # all point texts together
POINT_TOKENS = 90
MAX_POINTS = 8                   # per section
MANIFESTS = ("package.json", "pyproject.toml", "setup.cfg", "setup.py", "Cargo.toml", "go.mod",
             "CMakeLists.txt", "Makefile", "meson.build", "pom.xml", "build.gradle", "build.gradle.kts",
             "composer.json", "Gemfile")
DOC_DIRS = ("docs", "doc")
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
MIN_PART = 200                   # a cut file keeps at least this much, or it is skipped
#: Path words of the page's topics. Documentation files are taken in turn from each group, so one
#: large guide cannot crowd out the migration notes; files that match no group come last.
TOPIC_GROUPS = (("install", "getting-started", "getting_started", "quickstart", "quick-start", "usage",
                 "using", "setup"), ("build", "compil", "develop", "contribut"),
                ("packag", "bundl", "publish", "release", "deploy"), ("integrat",), ("migrat", "upgrad"))
TOPIC_WORDS = tuple(word for group in TOPIC_GROUPS for word in group)
TOPICS = {"install": ("Install and first use", "how a user adds it to a project and starts it"),
          "build": ("Build from source", "prerequisites, the build command and what it produces"),
          "test": ("Test and develop", "running tests, linters and the docs locally"),
          "package": ("Package and release", "bundle formats, entry points and publishing"),
          "integrate": ("Integrate with other tools", "frameworks, bundlers, module systems, types, platforms"),
          "migrate": ("Migrate between versions", "breaking changes and upgrade steps")}
CITE = re.compile(r"^(.+?):L?(\d+)(?:-L?(\d+))?$")


def _numbered(text: str, first: int = 1) -> str:
    return "\n".join(f"{number}| {line}" for number, line in enumerate(text.splitlines(), first))


def _head(text: str, room: int) -> str:
    """The longest whole-line prefix of ``text`` whose numbered form fits in ``room`` tokens."""
    lines = text.splitlines()
    low, high = 0, len(lines)
    while low < high:
        middle = (low + high + 1) // 2
        if count_text_tokens(_numbered("\n".join(lines[:middle]))) <= room:
            low = middle
        else:
            high = middle - 1
    return "\n".join(lines[:low])


def _candidates(repo: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """(README, build manifests, documentation files) under the repository root."""
    root = sorted(path for path in repo.iterdir() if path.is_file() and not path.is_symlink())
    readme = [path for path in root if path.stem.upper() == "README"
              and path.suffix.lower() in DOC_SUFFIXES | {""}][:1]
    manifests = [repo / name for name in MANIFESTS if (repo / name).is_file()]
    docs = [path for path in root if path not in readme and path.suffix.lower() in DOC_SUFFIXES
            and any(word in path.name.lower() for word in TOPIC_WORDS)]
    for name in DOC_DIRS:
        folder = repo / name
        if folder.is_dir():
            docs += [path for path in sorted(folder.rglob("*")) if path.is_file() and not path.is_symlink()
                     and path.suffix.lower() in DOC_SUFFIXES
                     and not any(part in DEFAULT_EXCLUDE_DIR_NAMES or part.startswith(".")
                                 for part in path.relative_to(repo).parts)]

    def group(path: Path) -> tuple[int, int]:
        """(topic group, 0 when the file name itself names it, 1 when only a directory does)."""
        for where, text in enumerate((path.name.lower(), path.relative_to(repo).as_posix().lower())):
            hit = next((number for number, words in enumerate(TOPIC_GROUPS) if any(w in text for w in words)), None)
            if hit is not None:
                return hit, where
        return len(TOPIC_GROUPS), 0
    queues: list[list[Path]] = [[] for _ in range(len(TOPIC_GROUPS) + 1)]
    for path in sorted(docs, key=lambda path: (group(path)[1], len(path.relative_to(repo).parts), path.as_posix())):
        queues[group(path)[0]].append(path)
    ordered = [queue[turn] for turn in range(max(map(len, queues[:-1]), default=0))
               for queue in queues[:-1] if turn < len(queue)]
    return readme, manifests, ordered + queues[-1]


def collect(repo: Path, tokens: int = DEFAULT_TOKENS) -> dict[str, Any]:
    """Choose and freeze the build task's input within ``tokens`` (numbered text, o200k_base).

    README (up to half the budget) and manifests come first, then documentation files in turn by
    topic (each up to a quarter). A file over its share is cut after a whole line; one that
    would keep under ``MIN_PART`` tokens is skipped and listed."""
    if tokens < 1:
        raise ValueError("the build page budget must be a positive number of tokens")
    readme, manifests, docs = _candidates(repo)
    files: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    room = tokens
    for kind, paths in (("readme", readme), ("manifest", manifests), ("docs", docs)):
        for path in paths:
            rel = path.relative_to(repo).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                skipped.append({"path": rel, "tokens": None, "reason": "not UTF-8 text"})
                continue
            full = count_text_tokens(_numbered(text))
            limit = min(room, {"readme": tokens // 2, "manifest": MANIFEST_TOKENS, "docs": tokens // 4}[kind])
            shown = text if full <= limit else _head(text, limit) if limit >= MIN_PART else ""
            if not shown.strip():
                skipped.append({"path": rel, "tokens": full, "reason": "over the budget"})
                continue
            used = count_text_tokens(_numbered(shown))
            room -= used
            files.append({"path": rel, "kind": kind, "tokens": used, "lines": len(text.splitlines()),
                          "shown_lines": len(shown.splitlines()), "text": shown,
                          "digest": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"budget": tokens, "files": files, "skipped": skipped,
            "read_tokens": sum(row["tokens"] for row in files)}


def summary(inputs: dict[str, Any]) -> dict[str, Any]:
    """What the run state keeps: the inputs without their text."""
    return {"budget": inputs["budget"], "read_tokens": inputs["read_tokens"],
            "files": [{key: row[key] for key in ("path", "kind", "tokens", "lines", "shown_lines")}
                      for row in inputs["files"]],
            "skipped": inputs["skipped"]}


def prompt(repo: str, inputs: dict[str, Any]) -> str:
    topics = "\n".join(f"- {key}: {heading}: {meaning}" for key, (heading, meaning) in TOPICS.items())
    blocks = "\n\n".join(f"=== {row['path']} (lines 1-{row['shown_lines']} of {row['lines']}) ===\n"
                         + _numbered(row["text"]) for row in inputs["files"])
    return (f'TASK: Write the "How to build and integrate" page for the repository "{repo}" from the '
            "files below: its README, part of its documentation and its build manifests, each line "
            "numbered. Cover only these topics, in this order, and skip a topic the files do not cover:\n"
            f"{topics}\n\n"
            'Return JSON {"sections":[{"topic":"build","points":[{"text":"...","cite":["PATH:START-END"]}]}]}. '
            "Each point is one or two sentences for a developer who wants to use, build or embed this project; "
            "name the command, file, option, package or version the files give, in backticks. Every point "
            "cites one to three line ranges of the files below that state it, as PATH:START-END with PATH "
            "exactly as in a === header; leave out anything no line states. A version-migration point names "
            f"the versions. At most {MAX_POINTS} points per topic, at most {POINT_TOKENS} tokens per point, "
            f"{ANSWER_TOKENS} tokens for all points together.\n\nFILES:\n\n{blocks}")


def _clean(value: Any, inputs: dict[str, Any]) -> tuple[list[dict], list[str]]:
    """The usable sections of an answer and every problem found on the way."""
    shown = {row["path"]: row["shown_lines"] for row in inputs["files"]}
    problems: list[str] = []
    sections: list[dict] = []
    raw = value.get("sections") if isinstance(value, dict) else None
    if not isinstance(raw, list):
        return [], ["sections must be a list"]
    budget = ANSWER_TOKENS
    for number, section in enumerate(raw, 1):
        topic = section.get("topic") if isinstance(section, dict) else None
        if topic not in TOPICS or any(row["topic"] == topic for row in sections):
            problems.append(f"section {number}: topic {topic!r} is unknown or repeated")
            continue
        points = []
        for index, point in enumerate(section.get("points") or [], 1):
            where = f"{topic} point {index}"
            text = " ".join(str(point.get("text") or "").split()) if isinstance(point, dict) else ""
            cites = point.get("cite") if isinstance(point, dict) else None
            cites = [cites] if isinstance(cites, str) else cites if isinstance(cites, list) else []
            good = []
            for cite in cites[:3]:
                match = CITE.match(str(cite).strip())
                start = int(match.group(2)) if match else 0
                end = int(match.group(3) or start) if match else 0
                if match and match.group(1) in shown and 1 <= start <= end <= shown[match.group(1)]:
                    good.append(f"{match.group(1)}:L{start}" + (f"-L{end}" if end != start else ""))
                else:
                    problems.append(f"{where}: citation {cite!r} names no shown file and line range")
            size = count_text_tokens(text)
            reason = ("no text" if not text else "no usable citation" if not good
                      else f"over {POINT_TOKENS} tokens" if size > POINT_TOKENS
                      else f"over {MAX_POINTS} points" if len(points) >= MAX_POINTS
                      else f"over the {ANSWER_TOKENS}-token answer" if size > budget else None)
            if reason:
                problems.append(f"{where}: dropped, {reason}")
                continue
            budget -= size
            points.append({"text": text, "cite": good})
        if points:
            sections.append({"topic": topic, "points": points})
        else:
            problems.append(f"section {topic}: no usable point")
    sections.sort(key=lambda row: list(TOPICS).index(row["topic"]))
    return sections, problems


def check(value: dict[str, Any], inputs: dict[str, Any]) -> None:
    sections, problems = _clean(value, inputs)
    if problems or not sections:
        raise ValueError("; ".join(problems[:12]) or "no section has a point")
    value["sections"] = sections


def normalize(value: Any, inputs: dict[str, Any]) -> list[str]:
    """Keep what passes and flag the rest; an answer with nothing usable stays an error."""
    sections, problems = _clean(value, inputs)
    if not sections:
        raise ValueError("no section has a cited point")
    value["sections"] = sections
    return problems


def _json_key_lines(text: str) -> dict[tuple[str, ...], int]:
    """Line of every object key in ``text``, by the path of keys that leads to that key.

    A key is recorded only where it opens an object of its own: the ``types`` inside
    ``exports`` is at ``("exports", ".", "types")`` and never answers for the top-level
    ``types``. Scalars and strings are read from the text, so a document that ``json``
    accepts gives every key it holds."""
    found: dict[tuple[str, ...], int] = {}
    stack: list[tuple[str, tuple[str, ...]]] = []          # (kind, path of this container)
    key, key_line = None, 0
    line, index = 1, 0
    while index < len(text):
        char = text[index]
        if char == "\n":
            line, index = line + 1, index + 1
        elif char in " \t\r":
            index += 1
        elif char == '"':
            start, chars = line, []
            index += 1
            while index < len(text):
                current = text[index]
                if current == "\\":
                    chars.append(text[index:index + 2])
                    index += 2
                    continue
                if current == "\n":
                    line += 1
                if current == '"':
                    index += 1
                    break
                chars.append(current)
                index += 1
            raw = "".join(chars)
            try:
                value = json.loads(f'"{raw}"')
            except ValueError:
                value = raw
            if stack and stack[-1][0] == "object" and key is None:
                key, key_line = value, start               # this string names a key
            elif key is not None:
                found[(*stack[-1][1], key)] = key_line     # a string value
                key = None
        elif char in "{[":
            inside = stack[-1][1] if stack else ()
            stack.append(("object" if char == "{" else "array", (*inside, key) if key is not None else inside))
            key, index = None, index + 1
        elif char in "}]":
            if stack:
                stack.pop()
            key, index = None, index + 1
        elif char == ",":
            key, index = None, index + 1
        elif char == ":":
            index += 1
        else:                                              # a number, true, false or null
            end = index
            while end < len(text) and text[end] not in ",}] \t\r\n":
                end += 1
            if key is not None:
                found[(*stack[-1][1], key)] = key_line
                key = None
            index = end
    return found


_SECTION = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*$")
_QUOTED_KEY = re.compile(r'^\s*"?([^"=\s]+)"?\s*=')


def _table_key_lines(text: str) -> dict[tuple[str, ...], int]:
    """Line of every TOML or INI key, by the table header it sits under.

    ``[tool.other] name`` does not answer for ``[project] name``, and a bracketed line
    inside a multi-line value is not a header."""
    found: dict[tuple[str, ...], int] = {}
    table: tuple[str, ...] = ()
    for number, line in enumerate(text.splitlines(), 1):
        if header := _SECTION.match(line):
            table = tuple(part.strip().strip("\"'") for part in header.group(1).split("."))
        elif match := _QUOTED_KEY.match(line):
            found.setdefault((*table, match.group(1)), number)
    return found


def _and(names: list[str]) -> str:
    quoted = [f"`{name}`" for name in names]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def facts(inputs: dict[str, Any]) -> tuple[list[str], set[str]]:
    """(the facts the program reads from the manifests, the manifests it read them from)."""
    rows: list[str] = []
    read: set[str] = set()
    for row in inputs["files"]:
        path, text = row["path"], row["text"]
        first = len(rows)

        def add(label: str, value: str, keys: tuple[str, ...], at: dict[tuple[str, ...], int]) -> None:
            line = at.get(keys)
            rows.append(f"- {label} `{value}` — `{path}:L{line}`" if line else f"- {label} `{value}` — `{path}`")

        try:
            if path in ("package.json", "composer.json"):
                data = json.loads(text)
                at = _json_key_lines(text)
                keys = (("name", "version") if path == "composer.json"
                        else ("name", "version", "main", "module", "types", "type"))
                for key in keys:
                    if isinstance(data.get(key), str):
                        add(f"package `{key}`", data[key], (key,), at)
                for name, command in list((data.get("scripts") or {}).items())[:20]:
                    add(f"script `{name}` runs", str(command), ("scripts", name), at)
                for key, label in (("peerDependencies", "peer dependency"), ("require", "requirement"),
                                   ("require-dev", "development requirement")):
                    required = data.get(key) or {}
                    for name in list(required)[:20]:
                        add(label if key == "peerDependencies" else f"{label} `{name}`",
                            name if key == "peerDependencies" else str(required[name]), (key, name), at)
            elif path == "setup.cfg":                              # INI, not TOML
                at = _table_key_lines(text)
                lines = text.splitlines()
                for table in ("metadata", "options"):
                    for key in ("name", "version", "python_requires"):
                        if line := at.get((table, key)):
                            add(f"`{key}`", lines[line - 1].split("=", 1)[1].strip(), (table, key), at)
            elif path in ("pyproject.toml", "Cargo.toml"):
                data = tomllib.loads(text)
                at = _table_key_lines(text)
                table = "project" if isinstance(data.get("project"), dict) else "package"
                project = data.get(table) or {}
                for key in ("name", "version", "requires-python", "rust-version"):
                    if isinstance(project.get(key), str):
                        add(f"`{key}`", project[key], (table, key), at)
                for name in project.get("scripts") or {}:
                    add("console script", name, (table, "scripts", name), at)
                for name in project.get("optional-dependencies") or {}:
                    add("optional extra / feature", name, (table, "optional-dependencies", name), at)
                for name in data.get("features") or {}:
                    add("optional extra / feature", name, ("features", name), at)
                backend = (data.get("build-system") or {}).get("build-backend")
                if backend:
                    add("build backend", backend, ("build-system", "build-backend"), at)
            elif path in ("go.mod", "CMakeLists.txt", "Makefile"):
                pattern = {"go.mod": r"^(module|go)\s+(\S+)",
                           "CMakeLists.txt": r"^\s*(project|add_library|add_executable|option)\s*\(\s*([\w.-]+)",
                           "Makefile": r"^()([A-Za-z0-9][\w.-]*)\s*:(?!=)"}[path]
                for match in list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))[:20]:
                    line = text.count("\n", 0, match.start()) + 1
                    rows.append(f"- {match.group(1).lower() or 'make target'} `{match.group(2)}` — `{path}:L{line}`")
        except (ValueError, tomllib.TOMLDecodeError, AttributeError, TypeError):
            rows.append(f"- `{path}` could not be parsed; its text is still among the sources read")
            continue
        if len(rows) > first:
            read.add(path)
    return rows, read


def no_task_note(inputs: dict[str, Any]) -> str:
    """The page's note when the plan queued no ``build`` task: no file, or no room for one."""
    over = [row for row in inputs["skipped"] if row.get("reason") == "over the budget"]
    if over:
        return (f"Found {len(over)} README, documentation or build-manifest file(s), but the "
                f"{inputs['budget']:,}-token budget left room for none of them, so no model was asked.")
    if inputs["skipped"]:
        return (f"Found {len(inputs['skipped'])} README, documentation or build-manifest file(s), but none "
                f"could be read as UTF-8 text within the {inputs['budget']:,}-token budget, so no model was asked.")
    return "No README, documentation or build manifest was found, so no model was asked."


def render(repo: str, inputs: dict[str, Any], answer: dict[str, Any] | None, note: str | None) -> str:
    """BUILD.md: program-read facts, the model's cited points, and the list of what was read."""
    found, read = facts(inputs)
    if read:
        header = f"The facts are read by the program from {_and(sorted(read))}; "
    elif found:
        header = "The program could not parse a fact from these build manifests; "
    else:
        header = "No build manifest here is one the program reads, so the page has no facts section; "
    header += ("each point below was written by a model and cites the lines it comes from, and the program "
               "checked that every cited file and line exists.")
    lines = [f"# {repo}: how to build and integrate", "",
             "Written from the README, documentation and build manifests listed at the end, not from the "
             "source.", header, ""]
    if note:
        lines += [note, ""]
    if found:
        lines += ["## Facts from the build manifests", "", *found, ""]
    for section in (answer or {}).get("sections") or []:
        lines += [f"## {TOPICS[section['topic']][0]}", ""]
        lines += [f"- {point['text']} ({', '.join(f'`{cite}`' for cite in point['cite'])})"
                  for point in section["points"]]
        lines.append("")
    lines += ["## Sources read", "",
              f"{inputs['read_tokens']:,} of {inputs['budget']:,} tokens (numbered lines):", ""]
    lines += [f"- `{row['path']}` — {row['tokens']:,} tokens"
              + (f", lines 1-{row['shown_lines']} of {row['lines']}" if row["shown_lines"] < row["lines"] else "")
              for row in inputs["files"]]
    if inputs["skipped"]:
        lines += ["", f"Skipped ({len(inputs['skipped'])}): "
                  + ", ".join(f"`{row['path']}`" for row in inputs["skipped"][:40])
                  + (" …" if len(inputs["skipped"]) > 40 else "")]
    return "\n".join(lines) + "\n"
