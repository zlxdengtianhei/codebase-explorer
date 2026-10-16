"""One call-resolution policy for normalized edges and capability counts."""
from __future__ import annotations

import ast
import builtins
import re


class CallResolver:
    def __init__(self, methods: list[dict], files=None, types=None):
        self.methods = {int(m["nodeId"]): m for m in methods if m.get("nodeId") is not None}
        self.files = set(files) if files is not None else {m.get("file", "") for m in methods if m.get("file")}
        self.python_modules = set()
        for path in self.files:
            if path.endswith(".py"):
                module = path[:-3].removesuffix("/__init__").removeprefix("src/")
                if "/" not in module:
                    self.python_modules.add(module)
        self.by_pair: dict[str, list[int]] = {}
        self.by_full: dict[str, list[int]] = {}
        self.classes = {"Self"}
        method_names = {m.get("fullName") for m in methods}
        # pysrc2cpg also emits TYPE_DECL for every function. Those entries
        # have the exact identity of a method, unlike their owning class.
        self.types = {t["fullName"]: t for t in (types or []) if t.get("file") in self.files
                      and not (str(t.get("file", "")).endswith(".py") and t["fullName"] in method_names)}
        self.types_by_name = {}
        for full, entry in self.types.items():
            name = entry.get("name") or full.split(".")[-1]
            self.classes.add(name)
            self.types_by_name.setdefault(name, []).append(full)
        for native, method in self.methods.items():
            full = method.get("fullName", "")
            self.by_full.setdefault(full, []).append(native)
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
        callees = call.get("callees") or []
        internal = list(dict.fromkeys(int(c["nodeId"]) for c in callees
                                     if not c.get("external") and c.get("nodeId") is not None
                                     and int(c["nodeId"]) in self.methods))
        if internal:
            return ("resolved" if len(internal) == 1 else "ambiguous", internal, [])
        full = call.get("methodFullName") or ""
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
        if full == "<unknownFullName>" or any(c.get("fullName") == "<unknownFullName>" for c in callees):
            return "unresolved", [], []
        exact = self.by_full.get(full, [])
        if exact:
            return ("resolved" if len(exact) == 1 else "ambiguous", exact, [])
        # A repository-qualified miss is analyzer guesswork, not a known
        # external target. Never salvage its last two components.
        if (any(full.startswith(path + ":") for path in self.files)
                or (".py:" in full and full.split(".py:", 1)[0] in self.python_modules)):
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
        external = list(dict.fromkeys(c.get("fullName") or call.get("name", "") for c in callees if c.get("external")))
        # An internal callee missing from the exported method set is unknown.
        return ("external", [], external) if external else ("unresolved", [], [])
