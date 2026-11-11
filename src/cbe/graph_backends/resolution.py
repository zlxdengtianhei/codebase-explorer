"""Import declaration resolution and file identity, shared by graph backends.

Resolution is static and repository bounded: it never imports project code or
searches the host environment. Absolute Python dependencies outside the source
roots are external, whether installed on this machine or not.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath

from ._paths import canonical_repo_path
from .identity import repository_files, file_id, external_id
from cbe.source_context import suffix_languages


# System header namespaces documented by POSIX Issue 8, <sys/...>,
# <netinet/in.h>, <arpa/inet.h>, and Linux man-pages, headers(7).
# These namespaces never establish a repository include search root.
SYSTEM_INCLUDE_PREFIXES = frozenset({"sys", "netinet", "arpa", "net", "linux", "asm", "asm-generic"})


def go_modules(repo: Path, files) -> dict[str, str]:
    """Read root and nested Go module identities without searching the host."""
    modules = {}
    for path in sorted(files):
        if PurePosixPath(path).name != "go.mod":
            continue
        try:
            text = (repo / path).read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"(?m)^\s*module\s+(\S+)\s*$", text)
        if match:
            parent = PurePosixPath(path).parent
            modules[match[1]] = "" if str(parent) == "." else str(parent)
    return modules


class ImportResolver:
    def __init__(self, repo: Path, files=None, suffix_map=None):
        self.repo = repo
        self.suffix_map = suffix_languages() if suffix_map is None else suffix_map
        self.files = repository_files(repo) if files is None else files
        self.suffix_files = {}
        for path in sorted(self.files):
            parts = path.split("/")
            for start in range(len(parts)):
                self.suffix_files.setdefault("/".join(parts[start:]), []).append(path)
        self.diagnostics = []
        self.include_basis = {}
        self.go_modules = go_modules(repo, self.files)
        self.python_roots = [""]
        # Locate import roots from package ancestry rather than assuming that
        # top-level packages live at the repository root (src/ is common).
        for path in self.files:
            if not path.endswith("/__init__.py"):
                continue
            package = PurePosixPath(path).parent
            top = package
            while str(top.parent) != "." and str(top.parent / "__init__.py") in self.files:
                top = top.parent
            root = "" if str(top.parent) == "." else str(top.parent) + "/"
            if root not in self.python_roots:
                self.python_roots.append(root)

    def python_file(self, module: str) -> str | None:
        stem = module.replace(".", "/")
        for root in self.python_roots:
            for candidate in (root + stem + "/__init__.py", root + stem + ".py"):
                if candidate in self.files:
                    return candidate
        return None

    def python_local(self, module: str) -> bool:
        top = module.split(".")[0]
        return any(p.startswith(root + top + "/") or p == root + top + ".py"
                   for root in self.python_roots for p in self.files)

    def _python(self, path: str, text: str) -> list[tuple[str, str | None]]:
        try:
            statement = ast.parse(text).body[0]
        except (SyntaxError, IndexError):
            return [("unresolved", None)]
        if isinstance(statement, ast.Import):
            modules = [alias.name for alias in statement.names]
            relative = False
        elif isinstance(statement, ast.ImportFrom):
            base = statement.module or ""
            relative = bool(statement.level)
            if relative:
                parent = list(PurePosixPath(path).parent.parts)
                if parent and parent[0] == "src" and "src/" in self.python_roots:
                    parent = parent[1:]
                if statement.level > len(parent):
                    return [("unresolved", None)]
                base = ".".join(parent[:len(parent) - statement.level + 1] + ([base] if base else []))
            modules = []
            for alias in statement.names:
                child = base + "." + alias.name if base else alias.name
                # An imported name can be a submodule or a symbol of the base.
                child_stem = child.replace(".", "/")
                namespace_child = any(p.startswith(root + child_stem + "/")
                                      for root in self.python_roots for p in self.files)
                modules.append(child if self.python_file(child) or namespace_child else base)
        else:
            return [("unresolved", None)]
        results = []
        for module in modules:
            target = self.python_file(module)
            # Scripts outside packages can import adjacent modules when run
            # directly. Keep this lookup repository bounded too.
            parent = PurePosixPath(path).parent
            if not relative and str(parent / "__init__.py") not in self.files:
                stem = str(parent / module.replace(".", "/"))
                target = next((p for p in (stem + ".py", stem + "/__init__.py") if p in self.files), target)
            if target:
                results.append(("resolved", target))
            elif relative or self.python_local(module):
                results.append(("unresolved", None))
            else:
                results.append(("external", module))
        return list(dict.fromkeys(results))

    def resolve(self, path: str, expression: str) -> list[tuple[str, str | None]]:
        text = (expression or "").strip()
        suffix = PurePosixPath(path).suffix.lower()
        language = self.suffix_map.get(suffix)
        suffix = {"c": ".c", "cpp": ".c", "ruby": ".rb", "php": ".php"}.get(language, suffix)
        if suffix == ".py":
            return self._python(path, text)
        if suffix in {".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".hh"}:
            match = re.fullmatch(r'#\s*include\s*([<"])([^>"]+)[>"]\s*', text)
            if not match:
                return [("unresolved", None)]
            delimiter, token = match.groups()
            local = canonical_repo_path(str(PurePosixPath(path).parent / token))
            if delimiter == '"' and local in self.files:
                return [("resolved", local)]
            matches = self.suffix_files.get(token, [])
            if delimiter == '"' and not matches:
                matches = self.suffix_files.get(PurePosixPath(token).name, [])
            if delimiter == "<":
                # A basename alone supplies no evidence of an include search
                # root. In particular, repository compatibility/test headers
                # must not shadow standard or third-party library headers.
                if token.split("/", 1)[0] in SYSTEM_INCLUDE_PREFIXES:
                    return [("external", token)]
                if len(matches) > 1:
                    self.diagnostics.append(dict(path=path, code="ambiguous_include",
                        expression=text, candidates=matches,
                        message=f"multiple repository candidates for <{token}>: {', '.join(matches)}"))
                    return [("unresolved", None)]
                if "/" not in token:
                    return [("external", token)]
                if len(matches) == 1:
                    prefix = str(PurePosixPath(token).parent)
                    self.include_basis[(path, text)] = {
                        "kind": "repository_directory_prefix", "prefix": prefix,
                        "include_root": matches[0][:-len(token)].rstrip("/") or ".",
                    }
                    return [("resolved", matches[0])]
                return [("external", token)]
            if len(matches) == 1:
                return [("resolved", matches[0])]
            return [("unresolved", None)]
        token = import_token(text, suffix, self.suffix_map)
        if not token:
            return [("unresolved", None)]
        if suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}:
            if not token.startswith("."):
                return [("external", token)]
            stem = canonical_repo_path(str(PurePosixPath(path).parent / token))
            if stem:
                extensions = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
                candidates = [stem] + [stem + ext for ext in extensions] + [stem + "/index" + ext for ext in extensions]
                # TypeScript source commonly imports the emitted JS filename.
                replacements = {".js": (".ts", ".tsx"), ".mjs": (".mts",), ".cjs": (".cts",)}
                for emitted, sources in replacements.items():
                    if stem.endswith(emitted):
                        candidates.extend(stem[:-len(emitted)] + ext for ext in sources)
                for candidate in candidates:
                    if candidate in self.files:
                        return [("resolved", candidate)]
        if suffix == ".rb":
            local = text.startswith("require_relative")
            stem = canonical_repo_path(str(PurePosixPath(path).parent / token)) if local else token
            for candidate in (stem, (stem or "") + ".rb"):
                if candidate in self.files:
                    return [("resolved", candidate)]
            return [("unresolved", None)] if local else [("external", token)]
        if suffix in {".java", ".kt", ".kts", ".cs", ".php", ".swift"}:
            # Class imports can include a member; try the owning file too.
            parts = token.replace("\\", ".").rstrip(".*").split(".")
            extensions = {".kts": (".kt", ".kts")}.get(suffix, (suffix,))
            for end in range(len(parts), 0, -1):
                stem = "/".join(parts[:end])
                matches = sorted(p for p in self.files if any(
                    p == stem + ext or p.endswith("/" + stem + ext) for ext in extensions))
                if matches:
                    return [("resolved", matches[0])] if len(matches) == 1 else [("unresolved", None)]
            return [("external", token)]
        if suffix == ".go":
            # A package import maps to every non-test Go source in its
            # directory. Exploding the declaration preserves real file
            # identities instead of inventing one representative file.
            for module, root in sorted(self.go_modules.items(), key=lambda row: len(row[0]), reverse=True):
                if token != module and not token.startswith(module + "/"):
                    continue
                relative = token[len(module):].lstrip("/")
                directory = PurePosixPath(root) / relative if relative else PurePosixPath(root)
                prefix = "" if str(directory) == "." else str(directory).rstrip("/") + "/"
                targets = sorted(path for path in self.files if path.startswith(prefix)
                                 and "/" not in path[len(prefix):] and path.endswith(".go")
                                 and not path.endswith("_test.go"))
                return [("resolved", path) for path in targets] or [("unresolved", None)]
            return [("external", token)]
        if suffix == ".rs":
            parts = token.split("::")
            if parts[0] not in {"crate", "self", "super"}:
                return [("external", token)]
            base = "src" if parts[0] == "crate" else str(PurePosixPath(path).parent)
            if parts[0] == "super":
                base = str(PurePosixPath(base).parent)
            for end in range(len(parts), 1, -1):
                stem = canonical_repo_path(str(PurePosixPath(base).joinpath(*parts[1:end])))
                for candidate in ((stem or "") + ".rs", (stem or "") + "/mod.rs"):
                    if candidate in self.files:
                        return [("resolved", candidate)]
            return [("unresolved", None)]
        return [("unresolved", None)]


def import_token(text: str, suffix: str, suffix_map=None) -> str | None:
    """Select syntax by source language; Python must never hit JS's `from`."""
    if suffix == ".py":
        try:
            statement = ast.parse(text).body[0]
        except (SyntaxError, IndexError):
            return None
        if isinstance(statement, ast.ImportFrom):
            return "." * statement.level + (statement.module or "")
        if isinstance(statement, ast.Import) and len(statement.names) == 1:
            return statement.names[0].name
        return None
    language = (suffix_languages() if suffix_map is None else suffix_map).get(suffix)
    suffix = {"ruby": ".rb", "php": ".php"}.get(language, suffix)
    patterns = {
        ".go": r'^import\s+(?:(?:\w+|\.)\s+)?["`]?([^"`\s]+)["`]?$',
        ".java": r"^import\s+(?:static\s+)?([\w.*]+)\s*;?$",
        ".kt": r"^import\s+([\w.*]+)(?:\s+as\s+\w+)?$",
        ".kts": r"^import\s+([\w.*]+)(?:\s+as\s+\w+)?$",
        ".cs": r"^(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;?$",
        ".rb": r'''^(?:require_relative|require)\s*\(?\s*["']([^"']+)["']''',
        ".rs": r"^use\s+([\w:]+)(?:\s+as\s+\w+)?\s*;?$",
        ".php": r"^use\s+(?:function\s+|const\s+)?([\w\\]+)(?:\s+as\s+\w+)?\s*;?$",
        ".swift": r"^import\s+(?:(?:class|struct|func|enum|protocol|var|let|typealias)\s+)?([\w.]+)$",
    }
    pattern = patterns.get(suffix, r'''(?:require\s*\(\s*|from\s*|import\s*)["']([^"']+)["']''')
    match = re.search(pattern, text)
    if match:
        return next((g for g in match.groups() if g), None)
    return text if text and not re.search(r"[\s()#]", text) else None


def resolve_declarations(repo: Path, nodes: list[dict], edges: list[dict], *, files=None, diagnostics=None, suffix_map=None) -> tuple[list[dict], list[dict]]:
    resolver = ImportResolver(repo, files, suffix_map)
    known = {n["id"] for n in nodes}
    result = []
    for edge in edges:
        if edge.get("kind") != "import" or edge.get("backend") != "joern":
            result.append(edge)
            continue
        for index, (status, target) in enumerate(resolver.resolve(edge.get("path") or "", edge.get("expression") or "")):
            target_id = (file_id(target, resolver.files) if status == "resolved" else external_id(target)) if target else None
            if target_id and target_id not in known:
                known.add(target_id)
                nodes.append({"id": target_id, "kind": "file" if status == "resolved" else "external",
                              "path": target if status == "resolved" else None,
                              "name": target, "start_line": None, "end_line": None,
                              "backend": "joern", **({"external": True} if status == "external" else {})})
            basis = resolver.include_basis.get((edge.get("path") or "", (edge.get("expression") or "").strip()))
            result.append({**edge, "id": edge["id"] + f"/{index}", "status": status, "target": target_id,
                           **({"resolution_basis": basis} if basis else {})})
    if diagnostics is not None:
        diagnostics.extend(resolver.diagnostics)
    return nodes, result
