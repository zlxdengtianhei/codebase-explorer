"""One call-resolution policy for normalized edges and capability counts."""
from __future__ import annotations

import ast
import builtins
import re


class CallResolver:
    def __init__(self, methods: list[dict]):
        self.methods = {int(m["nodeId"]): m for m in methods if m.get("nodeId") is not None}
        self.files = {m.get("file", "") for m in methods if m.get("file")}
        self.by_pair: dict[str, list[int]] = {}
        self.by_full: dict[str, list[int]] = {}
        for native, method in self.methods.items():
            full = method.get("fullName", "")
            self.by_full.setdefault(full, []).append(native)
            # Python frontend: path.py:<module>.Class.method. Do not match
            # a bare method name, which confuses unrelated receiver types.
            name = full.split(":")[-1]
            parts = name.split(".")
            if len(parts) >= 2 and not any(p.startswith("<") for p in parts[-2:]):
                self.by_pair.setdefault(".".join(parts[-2:]), []).append(native)

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
        if any(full.startswith(path + ":") for path in self.files):
            return "unresolved", [], []
        if re.fullmatch(r"[A-Za-z_]\w*\.[A-Za-z_]\w*", full):
            matches = self.by_pair.get(full, [])
            if matches:
                return ("resolved" if len(matches) == 1 else "ambiguous", matches, [])
        external = list(dict.fromkeys(c.get("fullName") or call.get("name", "") for c in callees if c.get("external")))
        # An internal callee missing from the exported method set is unknown.
        return ("external", [], external) if external else ("unresolved", [], [])
