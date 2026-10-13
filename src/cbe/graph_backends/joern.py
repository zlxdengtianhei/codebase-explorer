"""Joern backend for the ``cbe-graph/1`` contract.

This module wraps the upstream Joern CLI.  It does not re-implement any
language analysis: it runs ``joern-parse`` once per frontend flag, then a
small CPGQL export script that emits targeted JSON (methods, calls, control
flow, native REACHING_DEF definition-use edges, import declarations, and
optionally requested value-flow paths).

Identity rules:

* Caller/callee/CFG identity comes from Joern's native node ids, not from
  names.  Two files that both define ``helper`` cannot be confused.
* A call with several callees keeps the alternatives and reports
  ``ambiguous`` instead of inventing a single target.
* Data-flow identity is the native ``REACHING_DEF`` edge, not a
  parameter→return path.  Requested value-flow paths are a separate, clearly
  scoped, sampled query and are never labelled as intra-procedural analysis.
* Analysis failures are recorded as diagnostics/errors.  A thrown analyzer
  error is never converted into an apparently successful empty graph.

Provenance kept per relation: backend name/version, the language frontend and
the raw expression.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

#: language id (canonical, matches ``cbe.source_context``) -> Joern frontend
#: flag.  ``pythonsrc``/``javasrc`` are the source frontends; ``python``/``java``
#: select the removed py2cpg and the bytecode jimple frontend and are wrong for
#: source trees.
JOERN_LANGUAGE_FLAGS: dict[str, str] = {
    "c": "c",
    "cpp": "c",
    "python": "pythonsrc",
    "javascript": "javascript",
    "typescript": "javascript",
    "tsx": "javascript",
    "java": "javasrc",
    "go": "golang",
    "ruby": "rubysrc",
    "rust": "rust",
    "php": "php",
    "c_sharp": "csharpsrc",
    "kotlin": "kotlin",
    "swift": "swiftsrc",
}

#: Joern frontends that are intentionally outside the source-context surface
#: because they consume bytecode or binaries, not source.
JOERN_BYTECODE_FRONTENDS = frozenset({"jimple", "ghidra", "llvm"})

#: frontend flag -> Joern frontend name, for provenance.
FRONTEND_NAME = {
    "c": "c2cpg", "pythonsrc": "pysrc2cpg", "javascript": "jssrc2cpg",
    "javasrc": "javasrc2cpg", "golang": "gosrc2cpg", "rubysrc": "rubysrc2cpg",
    "rust": "rust2cpg", "php": "php2cpg", "csharpsrc": "csharpsrc2cpg",
    "kotlin": "kotlin2cpg", "swiftsrc": "swiftsrc2cpg",
}

#: Syntax noise that is not a user-visible call relation.
_SYNTHETIC_CALL = re.compile(r"^(?:<operator>|__ecma\.|_?tmp\d+\.)")

#: REACHING_DEF is capped so a very large program cannot exhaust the run dir.
DEFAULT_MAX_REACHING_DEFS = 50000


_EXPORT_SCRIPT = r"""
import io.shiftleft.codepropertygraph.generated.nodes.*
import io.joern.dataflowengineoss.language.*
import io.joern.dataflowengineoss.queryengine.EngineConfig
import java.nio.file.{Files, Paths}
import scala.util.{Try, Success, Failure}

@main def main(cpgFile: String, outFile: String, maxReachingDefs: Int,
               pathMethods: String, maxPathsPerMethod: Int): Unit = {
  val cpg = importCpg(cpgFile).get
  implicit val engineConfig: EngineConfig = EngineConfig()

  val realMethods: List[Method] = cpg.method.filterNot(m => m.isExternal || m.name == "<global>").l

  // Owner method of every AST node, from the AST itself.  This covers
  // parameters, parameter-out and method-return nodes uniformly.
  val ownerByNode: Map[Long, String] =
    realMethods.flatMap(m => m.ast.map(n => n.id -> m.fullName)).toMap

  def fileOf(n: AstNode): String =
    try n.file.name.headOption.getOrElse("") catch { case _: Throwable => "" }
  def ownerOf(n: AstNode): String = ownerByNode.getOrElse(n.id, "")
  def elemJson(n: AstNode): ujson.Obj = ujson.Obj(
    "label" -> n.label,
    "line" -> n.lineNumber.getOrElse(-1),
    "column" -> n.columnNumber.getOrElse(-1),
    "code" -> n.code.linesIterator.toList.headOption.getOrElse(""),
    "file" -> fileOf(n),
    "ownerMethod" -> ownerOf(n),
    "nodeId" -> n.id
  )

  val files = cpg.file.map(f => ujson.Obj("name" -> f.name, "hash" -> f.hash.getOrElse(""))).l

  val methods = realMethods.map { m =>
    ujson.Obj(
      "name" -> m.name,
      "fullName" -> m.fullName,
      "file" -> m.filename,
      "line" -> m.lineNumber.getOrElse(-1),
      "signature" -> m.signature,
      "nodeId" -> m.id
    )
  }.l

  val calls = cpg.call.filterNot(c => c.method.isExternal).map { c =>
    val callees = c.callee.map(m => ujson.Obj(
      "nodeId" -> m.id,
      "fullName" -> m.fullName,
      "external" -> m.isExternal,
      "file" -> m.filename,
      "line" -> m.lineNumber.getOrElse(-1)
    )).l
    ujson.Obj(
      "caller" -> c.method.fullName,
      "callerId" -> c.method.id,
      "callerFile" -> c.method.filename,
      "line" -> c.lineNumber.getOrElse(-1),
      "column" -> c.columnNumber.getOrElse(-1),
      "name" -> c.name,
      "code" -> c.code,
      "methodFullName" -> c.methodFullName,
      "callees" -> callees,
      "nodeId" -> c.id
    )
  }.l

  val cfg = realMethods.map { m =>
    val nodes = m.cfgNode.l
    val idx = nodes.zipWithIndex.map { case (n, i) => n.id -> i }.toMap
    val nodeJson = nodes.zipWithIndex.map { case (n, i) =>
      ujson.Obj(
        "i" -> i,
        "label" -> n.label,
        "line" -> n.lineNumber.getOrElse(-1),
        "column" -> n.columnNumber.getOrElse(-1),
        "order" -> n.order,
        "code" -> n.code.linesIterator.toList.headOption.getOrElse(""),
        "file" -> fileOf(n),
        "ownerMethod" -> ownerOf(n),
        "nodeId" -> n.id
      )
    }
    val edges = nodes.flatMap { n =>
      n.out("CFG").map { o =>
        val oc = o.asInstanceOf[CfgNode]
        ujson.Obj("from" -> idx.getOrElse(n.id, -1), "to" -> idx.getOrElse(oc.id, -1))
      }
    }
    ujson.Obj("method" -> m.fullName, "methodId" -> m.id, "file" -> m.filename,
              "line" -> m.lineNumber.getOrElse(-1), "nodeId" -> m.id,
              "nodes" -> nodeJson, "edges" -> edges)
  }.l

  val imports = cpg.imports.map { i =>
    val f = i.file.name.headOption.getOrElse("")
    ujson.Obj("file" -> f, "code" -> i.code.linesIterator.toList.headOption.getOrElse(""), "nodeId" -> i.id)
  }.l

  // Native REACHING_DEF definition-use edges: the bounded base data-flow graph.
  val rdSeen = scala.collection.mutable.Set[(Long, Long)]()
  val rdBuf = scala.collection.mutable.ArrayBuffer[ujson.Obj]()
  var rdTruncated = false
  realMethods.foreach { m =>
    m.ast.foreach { n =>
      if (!rdTruncated && n.label != "METHOD") {
        n.out("REACHING_DEF").foreach { o =>
          val t = o.asInstanceOf[AstNode]
          val key = (n.id, t.id)
          if (!rdSeen.contains(key)) {
            rdSeen.add(key)
            if (rdBuf.size >= maxReachingDefs) rdTruncated = true
            else rdBuf += ujson.Obj("source" -> elemJson(n), "target" -> elemJson(t))
          }
        }
      }
    }
  }

  // Optional, explicitly requested value-flow paths.  Separate scope; sampled;
  // the full path set is counted so the sample is visible.
  val requested = pathMethods.split(",").map(_.trim).filter(_.nonEmpty).toList
  val pathBuf = scala.collection.mutable.ArrayBuffer[ujson.Obj]()
  val errBuf = scala.collection.mutable.ArrayBuffer[ujson.Obj]()
  requested.foreach { name =>
    Try {
      cpg.method.filterNot(_.isExternal).name(name).foreach { m =>
        val paths = m.ast.isReturn.reachableByFlows(m.parameter).l
        paths.take(maxPathsPerMethod).foreach { p =>
          pathBuf += ujson.Obj(
            "method" -> m.fullName, "methodId" -> m.id,
            "totalPaths" -> paths.size, "sampled" -> (paths.size > maxPathsPerMethod),
            "scope" -> "value_flow_path",
            "elements" -> p.elements.toList.map(elemJson)
          )
        }
      }
    } match {
      case Failure(e) => errBuf += ujson.Obj(
        "method" -> name,
        "kind" -> e.getClass.getSimpleName,
        "message" -> Option(e.getMessage).getOrElse(""))
      case Success(_) => ()
    }
  }

  val root = ujson.Obj(
    "backend" -> "joern",
    "cpgFile" -> cpgFile,
    "files" -> files,
    "methods" -> methods,
    "calls" -> calls,
    "cfg" -> cfg,
    "imports" -> imports,
    "reachingDefs" -> rdBuf.toList,
    "reachingDefsTruncated" -> rdTruncated,
    "dataflowPaths" -> pathBuf.toList,
    "dataflowErrors" -> errBuf.toList
  )
  Files.write(Paths.get(outFile), ujson.write(root, indent = 2).getBytes("UTF-8"))
  println("WROTE " + outFile)
}
"""


class JoernError(RuntimeError):
    """Raised when the Joern CLI is missing or a whole run fails."""


def find_joern(joern_home: Path | str | None = None) -> Path | None:
    """Locate the Joern CLI directory that holds ``joern`` and ``joern-parse``."""

    candidates: list[Path] = []
    for base in (joern_home, os.environ.get("CBE_JOERN_HOME")):
        if not base:
            continue
        base = Path(base).expanduser()
        candidates += [base, base / "joern-cli", base / "bin"]
    which = shutil.which("joern")
    if which:
        candidates.append(Path(which).parent)
    for candidate in candidates:
        if (candidate / "joern").is_file() and (candidate / "joern-parse").is_file():
            return candidate
    return None


def _run(argv: list[str], timeout: int, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), check=False,
                          capture_output=True, text=True, timeout=timeout)


def joern_version(joern_bin: Path, timeout: int) -> str:
    try:
        completed = _run([str(joern_bin), "--version"], timeout=timeout, cwd=joern_bin.parent)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    for line in (completed.stdout + completed.stderr).splitlines():
        if line.strip().lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def build_with_joern(
    repo: Path,
    run_dir: Path,
    languages: list[str],
    joern_home: Path,
    timeout: int,
    *,
    max_reaching_defs: int = DEFAULT_MAX_REACHING_DEFS,
    dataflow_path_methods: list[str] | None = None,
    max_paths_per_method: int = 5,
) -> dict:
    """Parse each frontend's languages with Joern and return a normalized fragment.

    Returns ``{"backend", "nodes", "edges", "capabilities", "diagnostics",
    "raw"}``.  Raises :class:`JoernError` only when the CLI itself cannot run a
    frontend; per-language parse/export failures become ``failed`` capabilities
    plus diagnostics so a partial graph stays honest.
    """

    joern_bin = joern_home / "joern"
    parse_bin = joern_home / "joern-parse"
    run_dir.mkdir(parents=True, exist_ok=True)
    script = run_dir / "joern_export.sc"
    script.write_text(_EXPORT_SCRIPT, encoding="utf-8")

    version = joern_version(joern_bin, timeout)
    roots = [str(repo), str(joern_home)]
    diagnostics: list[dict] = []
    capabilities: list[dict] = []
    nodes: list[dict] = []
    edges: list[dict] = []
    raw: list[dict] = []
    path_methods = ",".join(dataflow_path_methods or [])

    by_language: dict[str, list[str]] = {}
    for language in languages:
        flag = JOERN_LANGUAGE_FLAGS.get(language)
        if flag is None:
            diagnostics.append({
                "path": None, "code": "language_unsupported",
                "message": f"joern backend has no source frontend mapping for language {language!r}",
            })
            capabilities.append(_capability(language, "call", "unsupported", version,
                                            backend="joern", limitations="no source frontend mapping"))
            continue
        by_language.setdefault(flag, []).append(language)

    for flag, langs in by_language.items():
        namespace = f"cpg:{flag}"
        cpg = run_dir / f"cpg-{flag}.bin"
        export = run_dir / f"cpg-{flag}.json"
        try:
            parsed = _run([str(parse_bin), str(repo), "--language", flag, "-o", str(cpg)],
                          timeout=timeout, cwd=run_dir)
        except subprocess.TimeoutExpired:
            for language in langs:
                capabilities.extend(_failed_capabilities(language, "joern", "backend_timeout"))
            diagnostics.append({"path": None, "code": "backend_timeout",
                                "message": f"joern-parse timed out after {timeout}s for frontend {flag}"})
            continue
        except OSError as exc:
            raise JoernError(f"cannot run joern-parse: {exc}") from exc
        parse_output = (parsed.stdout or "") + "\n" + (parsed.stderr or "")
        if parsed.returncode != 0 or not cpg.exists():
            for language in langs:
                capabilities.extend(_failed_capabilities(language, "joern", "backend_error"))
            message = f"joern-parse failed for frontend {flag} (exit {parsed.returncode})"
            cause = _first_error_line(parse_output, roots)
            if cause:
                message += f": {cause}"
            diagnostics.append({"path": None, "code": "backend_error", "message": message})
            continue
        try:
            exported = _run(
                [str(joern_bin), "--script", str(script),
                 "--param", f"cpgFile={cpg}", "--param", f"outFile={export}",
                 "--param", f"maxReachingDefs={max_reaching_defs}",
                 "--param", f"pathMethods={path_methods}",
                 "--param", f"maxPathsPerMethod={max_paths_per_method}", "--nocolors"],
                timeout=timeout, cwd=run_dir)
        except subprocess.TimeoutExpired:
            for language in langs:
                capabilities.extend(_failed_capabilities(language, "joern", "backend_timeout"))
            diagnostics.append({"path": None, "code": "backend_timeout",
                                "message": f"joern export timed out after {timeout}s for frontend {flag}"})
            continue
        if exported.returncode != 0 or not export.exists():
            for language in langs:
                capabilities.extend(_failed_capabilities(language, "joern", "backend_error"))
            diagnostics.append({"path": None, "code": "backend_error",
                                "message": f"joern export failed for frontend {flag} (exit {exported.returncode})"})
            continue
        try:
            payload = json.loads(export.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            for language in langs:
                capabilities.extend(_failed_capabilities(language, "joern", "backend_error"))
            diagnostics.append({"path": None, "code": "backend_error",
                                "message": f"joern export unreadable for frontend {flag}: {exc}"})
            continue
        payload["_languages"] = langs
        payload["_frontend"] = FRONTEND_NAME.get(flag, flag)
        raw.append(payload)
        f_nodes, f_edges = _normalize(payload, version, namespace)
        nodes.extend(f_nodes)
        edges.extend(f_edges)
        frontend_error = None
        if not payload.get("methods"):
            # joern-parse may have exited 0 after a frontend failed to load the
            # project; recover the real cause instead of reporting empty success.
            frontend_error = _frontend_error_from_direct_run(parse_output, run_dir, timeout, roots)
            if frontend_error:
                diagnostics.append({"path": None, "code": "frontend_error",
                                    "message": f"joern frontend {flag} reported an error while "
                                               f"producing no methods: {frontend_error}"})
        for language in langs:
            capabilities.extend(_capabilities_for(language, payload, version,
                                                  frontend_error=frontend_error))
        for error in payload.get("dataflowErrors", []):
            diagnostics.append({"path": None, "code": "dataflow_path_error",
                                "message": f"value-flow path query failed for {error.get('method')}: "
                                           f"{error.get('kind')}: {error.get('message')}"})
        if payload.get("reachingDefsTruncated"):
            diagnostics.append({"path": None, "code": "reaching_defs_truncated",
                                "message": f"REACHING_DEF export for frontend {flag} hit the "
                                           f"{max_reaching_defs}-edge cap"})

    # A whole-run CLI failure (OSError) raises above.  Per-frontend failures are
    # returned as ``failed`` capabilities + diagnostics so the exact cause
    # reaches the caller instead of a generic "no backend" error.
    if not raw and not (capabilities or diagnostics):
        diagnostics.append({"path": None, "code": "no_language_requested",
                            "message": "no Joern source language was requested"})
    return {
        "backend": {"name": "joern", "version": version},
        "nodes": nodes,
        "edges": edges,
        "capabilities": capabilities,
        "diagnostics": diagnostics,
        "raw": raw,
    }


def _norm_path(raw: str) -> str | None:
    """Normalize a Joern filename to a repo-relative POSIX path, or ``None``."""

    from ._paths import canonical_repo_path  # noqa: PLC0415

    return canonical_repo_path(raw)


_ERROR_MARKERS = re.compile(
    r"(?i)\b(?:error|exception|fail(?:ed|ure)?|not found|no such file|cannot run|unable to)\b")
_PRIMARY_CAUSE = re.compile(
    r"(?i)(failed to|cannot run|no such file|not found|unable to|are .{0,40}on your path|missing)")


def _scrub_text(text: str, roots: list[str]) -> str:
    scrubbed = text
    for root in roots:
        if root:
            scrubbed = scrubbed.replace(str(root), "<path>")
    return scrubbed


def _first_error_line(text: str, roots: list[str]) -> str | None:
    candidates = [line.strip() for line in (text or "").splitlines()
                  if _ERROR_MARKERS.search(line) and "process exited with code" not in line.lower()]
    if not candidates:
        return None
    primary = [line for line in candidates if _PRIMARY_CAUSE.search(line)]
    chosen = max(primary or candidates, key=len)
    return _scrub_text(chosen, roots)[:300]


def _frontend_error_from_direct_run(parse_output: str, run_dir: Path, timeout: int,
                                    roots: list[str]) -> str | None:
    """Re-run the exact frontend command ``joern-parse`` used, to capture its error.

    ``joern-parse`` can exit 0 while a frontend logged a load failure and wrote
    an empty CPG.  Only called when an export produced no methods, so a working
    language pays nothing for it.
    """

    match = re.search(r"invoke the frontend:\s*(.+)", parse_output or "")
    if not match:
        return None
    try:
        argv = shlex.split(match.group(1))
    except ValueError:
        return None
    if not argv:
        return None
    try:
        completed = _run(argv, timeout, run_dir)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return _first_error_line((completed.stdout or "") + "\n" + (completed.stderr or ""), roots)


def _visible_call(call: dict) -> bool:
    return not _SYNTHETIC_CALL.match(str(call.get("name", "")))


def _capability(language, graph, status, version, *, backend, limitations=None,
                condition=None, **extra) -> dict:
    entry = {"language": language, "graph": graph, "backend": backend,
             "version": version, "status": status}
    if limitations:
        entry["limitations"] = limitations
    if condition:
        entry["condition"] = condition
    entry.update(extra)
    return entry


def _failed_capabilities(language: str, backend: str, code: str) -> list[dict]:
    return [_capability(language, kind, "failed", None, backend=backend, limitations=code)
            for kind in ("call", "cfg", "dataflow", "import")]


def _normalize(payload: dict, version: str, namespace: str = "cpg") -> tuple[list[dict], list[dict]]:
    """Map a raw Joern export payload to standard nodes/edges.

    Every id is namespaced by the analyzed CPG and keyed on Joern's native
    node id, so same-name methods, overloads and independently numbered
    language CPGs cannot collide.
    """

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    def add_node(node_id: str, kind: str, *, path=None, start=None, end=None, name=None,
                 external=False, owner=None, joern_id=None, label=None, backend="joern") -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        entry = {"id": node_id, "kind": kind, "path": path, "start_line": start,
                 "end_line": end, "name": name, "backend": backend}
        if external:
            entry["external"] = True
        if owner:
            entry["owner"] = owner
        if label:
            entry["label"] = label
        if joern_id is not None:
            entry["analyzer_id"] = joern_id
        nodes.append(entry)

    method_by_native: dict[int, str] = {}
    for method in payload.get("methods", []):
        rel = _norm_path(method.get("file", ""))
        native = method.get("nodeId")
        node_id = f"{namespace}/method/{native}" if native is not None else \
            f"{namespace}/method/{rel}:{method.get('line', -1)}:{method.get('fullName', '')}"
        full = method.get("fullName") or method.get("name", "")
        add_node(node_id, "method" if "." in full else "function", path=rel,
                 start=method.get("line"), end=method.get("line"), name=full,
                 joern_id=native)
        if native is not None:
            method_by_native[int(native)] = node_id

    for call in payload.get("calls", []):
        if not _visible_call(call):
            continue
        rel = _norm_path(call.get("callerFile", ""))
        native_caller = call.get("callerId")
        caller = method_by_native.get(int(native_caller)) if native_caller is not None else None
        if caller is None:
            caller = f"{namespace}/caller/{rel}:{call.get('line', -1)}:{call.get('caller', '')}"
            add_node(caller, "function", path=rel, start=call.get("line"), name=call.get("caller"))
        internal: list[str] = []
        externals: list[str] = []
        for callee in call.get("callees", []) or []:
            native = callee.get("nodeId")
            full = callee.get("fullName") or call.get("name", "")
            if callee.get("external"):
                eid = f"{namespace}/ext/{full}"
                add_node(eid, "external", name=full, external=True, joern_id=native)
                externals.append(eid)
            else:
                mapped = method_by_native.get(int(native)) if native is not None else None
                if mapped is None:
                    mapped = f"{namespace}/ext/{full}"
                    add_node(mapped, "external", name=full, external=True, joern_id=native)
                internal.append(mapped)
        internal = list(dict.fromkeys(internal))
        externals = list(dict.fromkeys(externals))
        candidates = internal + externals
        if len(internal) == 1:
            target, status = internal[0], "resolved"
        elif len(internal) > 1:
            target, status = None, "ambiguous"
        elif externals:
            target, status = externals[0], "external"
        else:
            target, status = None, "unresolved"
        edge = {
            "id": f"{namespace}/call/{call.get('nodeId')}",
            "source": caller, "target": target, "kind": "call", "status": status,
            "path": rel, "line": call.get("line"), "column": call.get("column"),
            "expression": call.get("code"), "method_full_name": call.get("methodFullName"),
            "analyzer_id": call.get("nodeId"), "backend": "joern",
        }
        if len(candidates) > 1:
            edge["candidates"] = candidates
        edges.append(edge)

    for cfg in payload.get("cfg", []):
        method_native = cfg.get("methodId", cfg.get("nodeId"))
        owner_node = method_by_native.get(int(method_native)) if method_native is not None else None
        rel = _norm_path(cfg.get("file", ""))
        index_to_node: dict[int, str] = {}
        for node in cfg.get("nodes", []):
            i = node.get("i")
            node_id = f"{namespace}/cfg/{method_native}/{i}"
            index_to_node[i] = node_id
            add_node(node_id, "cfg_node", path=_norm_path(node.get("file", "")) or rel,
                     start=node.get("line"), end=node.get("line"), name=node.get("label"),
                     owner=owner_node, label=node.get("label"), joern_id=node.get("nodeId"))
        for edge in cfg.get("edges", []):
            source = index_to_node.get(edge.get("from"))
            target = index_to_node.get(edge.get("to"))
            if source is None or target is None:
                continue
            edges.append({
                "id": f"{namespace}/cfgedge/{method_native}/{edge.get('from')}->{edge.get('to')}",
                "source": source, "target": target, "kind": "cfg", "status": "resolved",
                "path": rel, "owner": owner_node, "backend": "joern",
            })

    for imp in payload.get("imports", []):
        rel = _norm_path(imp.get("file", ""))
        file_id = f"file:{rel}" if rel else None
        if file_id:
            add_node(file_id, "file", path=rel, name=Path(rel).name)
        edges.append({
            "id": f"{namespace}/import/{imp.get('nodeId')}",
            "source": file_id, "target": None, "kind": "import", "status": "unresolved",
            "path": rel, "expression": imp.get("code"), "analyzer_id": imp.get("nodeId"),
            "backend": "joern",
        })

    def add_flow_node(element: dict) -> str:
        eid = f"{namespace}/dfn/{element.get('nodeId')}"
        add_node(eid, "dataflow_node", path=_norm_path(element.get("file", "")),
                 start=element.get("line"), end=element.get("line"),
                 name=element.get("label"), owner=element.get("ownerMethod"),
                 label=element.get("label"), joern_id=element.get("nodeId"))
        return eid

    for rd in payload.get("reachingDefs", []):
        source_el = rd.get("source", {})
        target_el = rd.get("target", {})
        source = add_flow_node(source_el)
        target = add_flow_node(target_el)
        same_owner = (source_el.get("ownerMethod") and
                      source_el.get("ownerMethod") == target_el.get("ownerMethod"))
        edges.append({
            "id": f"{namespace}/rd/{source_el.get('nodeId')}->{target_el.get('nodeId')}",
            "source": source, "target": target, "kind": "dataflow", "status": "resolved",
            "path": _norm_path(source_el.get("file", "")),
            "scope": "reaching_def_intra" if same_owner else "reaching_def_inter",
            "backend": "joern",
        })

    for path in payload.get("dataflowPaths", []):
        method_native = path.get("methodId")
        previous = None
        for position, element in enumerate(path.get("elements", [])):
            eid = add_flow_node(element)
            if previous is not None:
                edges.append({
                    "id": f"{namespace}/vfp/{method_native}/{position}",
                    "source": previous, "target": eid, "kind": "dataflow", "status": "resolved",
                    "path": _norm_path(element.get("file", "")), "scope": "value_flow_path",
                    "sampled": bool(path.get("sampled")), "backend": "joern",
                })
            previous = eid

    return nodes, edges


def _capabilities_for(language: str, payload: dict, version: str,
                      *, frontend_error: str | None = None) -> list[dict]:
    if frontend_error:
        return [_capability(language, kind, "failed", version, backend="joern",
                            limitations=f"frontend error: {frontend_error}")
                for kind in ("call", "cfg", "dataflow", "import")]
    calls = [call for call in payload.get("calls", []) if _visible_call(call)]
    resolved = sum(1 for call in calls if _call_status(call) == "resolved")
    external = sum(1 for call in calls if _call_status(call) == "external")
    ambiguous = sum(1 for call in calls if _call_status(call) == "ambiguous")
    unresolved = len(calls) - resolved - external - ambiguous

    if resolved and not (ambiguous or unresolved):
        call_status = "resolved"
    elif calls:
        call_status = "partial"
    else:
        call_status = "empty"

    cfg_methods = sum(1 for cfg in payload.get("cfg", []) if cfg.get("edges"))
    rd_edges = len(payload.get("reachingDefs", []))
    has_methods = bool(payload.get("methods"))
    if rd_edges:
        df_status = "resolved"
    elif has_methods:
        df_status = "empty"
    else:
        df_status = "unsupported"

    conditions = []
    if language == "cpp":
        conditions.append("virtual/abstract calls bind to the static base declaration")
    if language in ("c", "cpp", "java", "go", "c_sharp"):
        conditions.append("coverage depends on the build/compiler configuration given to the frontend")
    if language in ("javascript", "typescript", "tsx", "python", "ruby"):
        conditions.append("dynamic dispatch and monkey-patching can hide call targets")
    if language == "ruby":
        conditions.append("rubysrc2cpg skips paths whose component is test, tests or spec")
    if language == "rust":
        conditions.append("rust2cpg requires a Cargo project layout (Cargo.toml + src)")
    if language == "php":
        conditions.append("php2cpg requires a PHP >= 7 runtime on PATH")
    if language == "swift":
        conditions.append("swiftsrc2cpg parses files independently; cross-file calls may stay external")
    if language == "c_sharp":
        conditions.append("cross-file resolution needs a shared namespace or project")
    call_notes = []
    if external:
        call_notes.append(f"{external} external")
    if ambiguous:
        call_notes.append(f"{ambiguous} ambiguous (multiple callees preserved)")
    if unresolved:
        call_notes.append(f"{unresolved} unresolved")
    if not calls:
        call_notes.append("analyzer ran but produced no user-visible calls")

    return [
        _capability(language, "call", call_status, version, backend="joern",
                    limitations="; ".join(call_notes) or None,
                    condition="; ".join(conditions) or None,
                    resolved=resolved, external=external, ambiguous=ambiguous,
                    unresolved=unresolved),
        _capability(language, "cfg", "resolved" if cfg_methods else ("empty" if has_methods else "unsupported"),
                    version, backend="joern", methods_with_edges=cfg_methods),
        _capability(language, "dataflow", df_status, version, backend="joern",
                    scope="reaching_def", reaching_def_edges=rd_edges,
                    limitations=None if rd_edges else "analyzer ran but produced no REACHING_DEF edges",
                    condition="local reaching definitions; inter-procedural value-flow paths are a separate opt-in query"),
        _capability(language, "import",
                    "partial" if payload.get("imports") else ("empty" if has_methods else "unsupported"),
                    version, backend="joern",
                    limitations="import/include declarations only; not resolved to target files"),
    ]


def _call_status(call: dict) -> str:
    internal = [c for c in call.get("callees", []) or [] if not c.get("external")]
    externals = [c for c in call.get("callees", []) or [] if c.get("external")]
    if len(internal) == 1:
        return "resolved"
    if len(internal) > 1:
        return "ambiguous"
    if externals:
        return "external"
    return "unresolved"
