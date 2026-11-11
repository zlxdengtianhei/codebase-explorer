"""One call-resolution policy for normalized edges and capability counts."""
from __future__ import annotations

import ast
import builtins
from pathlib import PurePosixPath
import posixpath
import re


_UNKNOWN_NAMES = ("<unresolvedNamespace>", "<unresolvedName>", "<unresolvedSignature>",
                  "<unknownFullName>", "<empty>")


class CallResolver:
    def __init__(self, methods: list[dict], files=None, types=None, go_modules=None,
                 javascript_packages=None):
        self.methods = {int(m["nodeId"]): m for m in methods if m.get("nodeId") is not None}
        self.method_names = {m.get("name") for m in methods}
        self.files = set(files) if files is not None else {m.get("file", "") for m in methods if m.get("file")}
        self.diagnostics: list[dict] = []
        self.go_modules = go_modules or {}
        self.javascript_packages = set(javascript_packages or ())
        self.python_modules = set()
        self.python_top_modules = set()
        for path in self.files:
            if path.endswith(".py"):
                module = path[:-3].removesuffix("/__init__").removeprefix("src/")
                self.python_modules.add(PurePosixPath(path).stem)
                top = module.split("/", 1)[0]
                if top:
                    self.python_top_modules.add(top)
                    self.python_modules.add(top)
        self.by_file: dict[str, dict[str, list[int]]] = {}
        self.by_pair: dict[str, list[int]] = {}
        self.by_full: dict[str, list[int]] = {}
        self.internal_prefixes = set()
        self.classes = {"Self"}
        method_names = {m.get("fullName") for m in methods}
        # pysrc2cpg also emits TYPE_DECL for every function. Those entries
        # have the exact identity of a method, unlike their owning class.
        self.types = {t["fullName"]: t for t in (types or []) if t.get("file") in self.files
                      and not (str(t.get("file", "")).endswith(".py") and t["fullName"] in method_names)}
        self.types_by_name = {}
        for full, entry in self.types.items():
            name = entry.get("name") or full.split(".")[-1]
            self.internal_prefixes.add(full)
            if "." in full and not str(entry.get("file", "")).endswith(".py"):
                self.internal_prefixes.add(full.rsplit(".", 1)[0])
            self.classes.add(name)
            self.types_by_name.setdefault(name, []).append(full)
        for native, method in self.methods.items():
            full = method.get("fullName", "")
            owner = full.rsplit(".", 1)[0]
            if (owner and owner != full and "<clinit>" not in full
                    and not str(method.get("file", "")).endswith(".py")):
                self.internal_prefixes.add(owner)
            self.by_full.setdefault(full, []).append(native)
            by_file = self.by_file.setdefault(method.get("file", ""), {})
            by_file.setdefault(full.partition(":")[2], []).append(native)
            member = full.rsplit(":", 1)[-1]
            if member != full.partition(":")[2]:
                by_file.setdefault(member, []).append(native)
            # Python frontend: path.py:<module>.Class.method. Do not match
            # a bare method name, which confuses unrelated receiver types.
            name = full.split(":")[-1]
            parts = name.split(".")
            if len(parts) >= 2 and not any(p.startswith("<") for p in parts[-2:]):
                self.by_pair.setdefault(".".join(parts[-2:]), []).append(native)
                if (str(method.get("file", "")).endswith(".py") and ":<module>." in full
                        and full.rsplit(".", 1)[0] not in method_names):
                    self.classes.add(parts[-2])

    def inherited_targets(self, receiver, name, call):
        if receiver in {"Self", "te.Self"}:
            native_caller = call.get("callerId")
            caller = self.methods.get(int(native_caller), {}) if native_caller is not None else {}
            owners = [caller.get("fullName", "").rsplit(".", 1)[0]]
        else:
            owners = self.types_by_name.get(receiver, [])
        if len(owners) != 1:
            return []
        visited = set()
        def search(owner):
            if owner in visited:
                return []
            visited.add(owner)
            direct = self.by_full.get(owner + "." + name, [])
            if direct:
                return direct
            targets = []
            for base in self.types.get(owner, {}).get("inherits", []):
                # Only traverse exact analyzer type identities. A short-name
                # collision is insufficient evidence of an inheritance edge.
                targets.extend(search(base))
            return targets
        return list(dict.fromkeys(search(owners[0])))

    def resolve(self, call: dict) -> tuple[str, list[int], list[str]]:
        result = self._resolve(call)
        status, _, external_names = result
        # Enforce Python's external identity contract at the single exit,
        # including future policy branches that return an external target.
        if (status == "external" and str(call.get("callerFile", "")).endswith(".py")
                and (not external_names or any(".py:" not in name and not name.startswith("__builtin")
                                               for name in external_names))):
            self.diagnostics.append({
                "path": call.get("callerFile"), "line": call.get("line"),
                "code": "python_external_name_unverified", "analyzer_id": call.get("nodeId"),
                "message": f"Python external target lacks a library identity: {external_names!r}",
            })
            return "unresolved", [], []
        return result

    def _resolve(self, call: dict) -> tuple[str, list[int], list[str]]:
        callees = call.get("callees") or []
        internal = list(dict.fromkeys(int(c["nodeId"]) for c in callees
                                     if not c.get("external") and c.get("nodeId") is not None
                                     and int(c["nodeId"]) in self.methods))
        full = call.get("methodFullName") or ""
        if internal:
            # Name-only binding with an unknown receiver is not a resolution.
            if full == "<unknownFullName>":
                return "ambiguous", internal, []
            return ("resolved" if len(internal) == 1 else "ambiguous", internal, [])
        # Python's frontend leaves builtin exception constructors without any
        # callee and with an unknown full name. A known builtin expression is
        # stronger evidence than that missing analyzer name.
        if not callees and str(call.get("callerFile", "")).endswith(".py"):
            try:
                expression = ast.parse(call.get("code", ""), mode="eval").body
            except SyntaxError:
                expression = None
            if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name):
                name = expression.func.id
                if callable(getattr(builtins, name, None)):
                    return "external", [], ["__builtin." + name]
        if any(marker in full for marker in _UNKNOWN_NAMES) or any(
                any(marker in str(c.get("fullName") or "") for marker in _UNKNOWN_NAMES) for c in callees):
            return "unresolved", [], []
        relative = self._relative_typescript_target(call, full)
        if relative is not None:
            return relative
        # A leading // is a relative import whose package prefix was lost.
        # Search only package ancestors; an unrelated basename is not evidence.
        if full.startswith("//") and ".py:<module>." in full and str(call.get("callerFile", "")).endswith(".py"):
            relative, _, member = full[2:].partition(":")
            caller = PurePosixPath(call["callerFile"])
            candidates = {str(parent / relative) for parent in caller.parents} & self.files
            if len(candidates) == 1:
                matches = self.by_file.get(next(iter(candidates)), {}).get(member, [])
                if len(matches) == 1:
                    return "resolved", matches, []
            return "unresolved", [], []
        exact = self.by_full.get(full, [])
        if exact:
            return ("resolved" if len(exact) == 1 else "ambiguous", exact, [])
        # A repository-qualified miss is analyzer guesswork, not a known
        # external target. Never salvage its last two components.
        if self._repository_qualified(full):
            return "unresolved", [], []
        if re.fullmatch(r"[A-Za-z_]\w*\.[A-Za-z_]\w*", full):
            matches = self.by_pair.get(full, [])
            if matches:
                return ("resolved" if len(matches) == 1 else "ambiguous", matches, [])
        receiver, _, name = full.rpartition(".")
        if ((".py:" not in full and full.split(".", 1)[0] in self.classes)
                or full.startswith("te.Self.")):
            matches = self.inherited_targets(receiver, name, call)
            if matches:
                return ("resolved" if len(matches) == 1 else "ambiguous", matches, [])
            return "unresolved", [], []
        if (".py:" not in full and not full.startswith("__builtin")
                and ("<returnValue>" in full or "<member>(" in full
                     or (str(call.get("callerFile", "")).endswith(".py")
                         and full.split(".", 1)[0] in self.python_modules))):
            return "unresolved", [], []
        external = list(dict.fromkeys(c.get("fullName") or call.get("name", "") for c in callees if c.get("external")))
        if (full.startswith("ANY.") and str(call.get("callerFile", "")).endswith(
                (".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".go"))):
            return "unresolved", [], []
        if str(call.get("callerFile", "")).endswith((".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")):
            if (not full.startswith(("std.", "__gnu"))
                    and re.fullmatch(r"(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\.\1(?::.*)?", full)):
                return "unresolved", [], []
            if full.split(":", 1)[0] in self.method_names:
                return "unresolved", [], []
        if any(self._repository_qualified(name) for name in external):
            return "unresolved", [], []
        # An internal callee missing from the exported method set is unknown.
        return ("external", [], external) if external else ("unresolved", [], [])

    def _repository_qualified(self, full: str) -> bool:
        if any(full.startswith(path + ":") for path in self.files):
            return True
        if ".py:" in full:
            module = full.split(".py:", 1)[0]
            if any(module == top or module.startswith(top + "/") for top in self.python_top_modules):
                return True
        if any(full == module or full.startswith(module + ".") or full.startswith(module + "/")
               for module in self.go_modules):
            return True
        if any(full == package or full.startswith(package + ":") for package in self.javascript_packages):
            return True
        return any(prefix and full.startswith(prefix + ".") for prefix in self.internal_prefixes)

    def _relative_typescript_target(self, call: dict, full: str):
        path = str(call.get("callerFile", ""))
        if not path.endswith((".ts", ".tsx", ".mts", ".cts")) or ":" not in full:
            return None
        relative, _, member = full.partition(":")
        if not relative.endswith((".js", ".jsx", ".mjs", ".cjs")):
            return None
        stem = posixpath.normpath(posixpath.join(posixpath.dirname(path), relative))
        if stem == ".." or stem.startswith("../"):
            return "unresolved", [], []
        replacements = {".js": (".ts", ".tsx"), ".jsx": (".tsx",),
                        ".mjs": (".mts",), ".cjs": (".cts",)}
        suffix = next(suffix for suffix in replacements if stem.endswith(suffix))
        base = stem[:-len(suffix)]
        candidates = [base + ext for ext in replacements[suffix]]
        candidates += [base + "/index" + ext for ext in (".ts", ".tsx")]
        candidates = [candidate for candidate in candidates if candidate in self.files]
        matches = list(dict.fromkeys(
            native for candidate in candidates
            for native in self.by_file.get(candidate, {}).get(member, [])))
        if len(matches) == 1:
            return "resolved", matches, []
        if len(matches) > 1:
            return "ambiguous", matches, []
        return ("unresolved", [], []) if candidates else None
