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


class ImportResolver:
    def __init__(self, repo: Path, files=None):
        self.repo = repo
        self.files = repository_files(repo) if files is None else files
        self.suffix_files = {}
        for path in sorted(self.files):
            parts = path.split("/")
            for start in range(len(parts)):
                self.suffix_files.setdefault("/".join(parts[start:]), []).append(path)
        self.python_roots = [""]
        if "src" in {p.split("/")[0] for p in self.files} and "src/__init__.py" not in self.files:
            self.python_roots.append("src/")

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
        language = suffix_languages().get(suffix)
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
            if len(matches) == 1:
                return [("resolved", matches[0])]
            return [("external", token)] if delimiter == "<" else [("unresolved", None)]
        token = import_token(text, suffix)
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
            # A Go import names a package, not an individual source file. Do
            # not invent one for local packages with multiple files.
            mod = self.repo / "go.mod"
            if mod.is_file():
                match = re.search(r"(?m)^module\s+(\S+)", mod.read_text(encoding="utf-8"))
                if match and (token == match[1] or token.startswith(match[1] + "/")):
                    return [("unresolved", None)]
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


def import_token(text: str, suffix: str) -> str | None:
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
    language = suffix_languages().get(suffix)
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


def resolve_declarations(repo: Path, nodes: list[dict], edges: list[dict], *, files=None) -> tuple[list[dict], list[dict]]:
    resolver = ImportResolver(repo, files)
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
            result.append({**edge, "id": edge["id"] + f"/{index}", "status": status, "target": target_id})
    return nodes, result
