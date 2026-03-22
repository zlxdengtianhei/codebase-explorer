"""Codebase Explorer MCP Server -- FastMCP entry point with 15 tools."""
from __future__ import annotations
import logging, os, uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field
from src.budget.controller import AnalysisBudgetController
from src.budget.estimator import estimate_tokens_from_lines
from src.doc.depth_planner import plan_doc_structure as _plan_doc_structure
from src.doc.generator import DocumentGenerator
from src.doc.mermaid import MermaidGenerator
from src.doc.templates import TemplateRenderer
from src.graph.dependency import (build_dependency_graph, get_dependency_graph_mermaid,
    get_module_dependency_subgraph)
from src.graph.grouper import group_modules, get_module_metrics
from src.graph.ordering import topological_order
from src.parser.codebase import CodebaseParser, CodebaseParseError
from src.state.checkpoint import CheckpointManager
from src.state.database import Database
from src.state.models import (AnalysisResult, AnalysisTask, DocNode, ModuleRecord, ProjectRecord)

logger = logging.getLogger(__name__)
DB_PATH = Path(os.environ.get("CODEBASE_EXPLORER_DB",
    str(Path.home() / ".codebase-explorer" / "state.db")))
_Str = Annotated[str | None, Field(description="Project ID. None = latest.")]

@asynccontextmanager
async def _lifespan(server: FastMCP):
    db = Database(DB_PATH)
    await db.initialize()
    try:
        yield {"db": db, "parser": CodebaseParser(), "ckpt": CheckpointManager(db),
               "budgets": {}, "docgen": DocumentGenerator(TemplateRenderer(), MermaidGenerator())}
    finally:
        await db.close()

mcp = FastMCP("codebase-explorer",
    instructions="Code analysis and progressive-disclosure doc generation server.",
    lifespan=_lifespan)

def _lc(ctx): return ctx.request_context.lifespan_context
def _db(ctx) -> Database: return _lc(ctx)["db"]
def _parser(ctx) -> CodebaseParser: return _lc(ctx)["parser"]
def _ckpt(ctx) -> CheckpointManager: return _lc(ctx)["ckpt"]
def _budgets(ctx) -> dict: return _lc(ctx)["budgets"]
def _docgen(ctx) -> DocumentGenerator: return _lc(ctx)["docgen"]
def _uid(): return uuid.uuid4().hex[:8]
def _now(): return datetime.now(UTC)

async def _proj(ctx, pid):
    p = await _db(ctx).get_project(pid) if pid else await _db(ctx).get_latest_project()
    if p is None: raise ToolError("No project found. Call index_codebase first.")
    return p
@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True})
async def index_codebase(
    path: Annotated[str, Field(description="Absolute path to the codebase root")],
    languages: Annotated[list[Literal["python", "typescript", "javascript"]] | None,
        Field(description="Languages to analyze. None = auto-detect.")] = None,
    ctx: Context = None,
) -> dict:
    """Parse source files, build dependency graph, group modules, store in DB."""
    resolved = Path(path).resolve()
    if not resolved.is_dir(): raise ToolError(f"Not a directory: {path}")
    db, parser, pid = _db(ctx), _parser(ctx), _uid()
    try: snap = parser.parse(str(resolved), languages=languages)
    except CodebaseParseError as e: raise ToolError(str(e)) from e
    gr = build_dependency_graph(snap)
    gp = group_modules(gr.graph, snap)
    proj = ProjectRecord(id=pid, path=str(resolved), created_at=_now(), status="indexed",
        languages=list(snap.languages_detected), file_count=len(snap.files),
        function_count=len(snap.functions), class_count=len(snap.classes),
        total_lines=snap.total_lines)
    await db.insert_project(proj)
    mods = []
    for name, files in gp.modules.items():
        fis = [f for f in snap.files if f.filepath in set(files)]
        mods.append(ModuleRecord(id=f"{pid}_{name}", project_id=pid, name=name,
            files=list(files), file_count=len(files),
            line_count=sum(f.line_count for f in fis),
            function_count=sum(len(f.function_names) for f in fis),
            class_count=sum(len(f.class_names) for f in fis),
            is_utility=name in gp.utility_files))
    await db.insert_modules(mods)
    return {"status": "success",
        "summary": f"Indexed {len(snap.files)} files, {len(snap.functions)} functions",
        "data": {"project_id": pid, "file_count": len(snap.files),
            "function_count": len(snap.functions), "class_count": len(snap.classes),
            "languages": list(snap.languages_detected), "module_count": gp.module_count}}
@mcp.tool(annotations={"readOnlyHint": True})
async def get_modules(
    project_id: _Str = None,
    sort_by: Annotated[Literal["name", "size", "complexity", "dependency"],
        Field(description="Sort order.")] = "name",
    ctx: Context = None,
) -> dict:
    """List detected modules with metrics."""
    proj = await _proj(ctx, project_id)
    items = [{"name": m.name, "file_count": m.file_count, "line_count": m.line_count,
        "function_count": m.function_count, "class_count": m.class_count,
        "is_utility": m.is_utility} for m in await _db(ctx).get_modules(proj.id)]
    if sort_by == "size": items.sort(key=lambda m: m["line_count"], reverse=True)
    elif sort_by == "complexity":
        items.sort(key=lambda m: m["function_count"] + m["class_count"] * 3, reverse=True)
    return {"status": "success",
        "data": {"project_id": proj.id, "modules": items, "total_modules": len(items)}}
@mcp.tool(annotations={"readOnlyHint": True})
async def get_module_detail(
    module_name: Annotated[str, Field(description="Module name")],
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Get file list, interfaces, dependencies for a module."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    mod = await db.get_module(proj.id, module_name)
    if mod is None: raise ToolError(f"Module '{module_name}' not found")
    res = await db.get_result(proj.id, module_name)
    analysis = ({"description": res.description, "public_interfaces": res.public_interfaces,
        "dependencies": res.dependencies, "dependents": res.dependents,
        "mermaid_diagram": res.mermaid_diagram} if res else None)
    return {"status": "success", "data": {"name": mod.name, "files": mod.files,
        "file_count": mod.file_count, "line_count": mod.line_count,
        "function_count": mod.function_count, "class_count": mod.class_count,
        "is_utility": mod.is_utility, "description": mod.description, "analysis": analysis}}
@mcp.tool(annotations={"readOnlyHint": True})
async def get_dependency_graph(
    scope: Annotated[Literal["project", "module"],
        Field(description="'project' or 'module'.")] = "project",
    target: Annotated[str | None, Field(description="Module name for scope=module.")] = None,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Get dependency graph as Mermaid diagram."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    gr = build_dependency_graph(_parser(ctx).parse(proj.path))
    if scope == "module":
        if not target: raise ToolError("'target' required for scope='module'")
        mod = await db.get_module(proj.id, target)
        if mod is None: raise ToolError(f"Module '{target}' not found")
        mermaid = get_dependency_graph_mermaid(
            get_module_dependency_subgraph(gr.graph, mod.files))
    else: mermaid = get_dependency_graph_mermaid(gr.graph)
    return {"status": "success", "data": {"scope": scope, "target": target,
        "mermaid_graph": mermaid, "node_count": gr.file_count, "edge_count": gr.edge_count,
        "circular_deps": [list(c) for c in gr.circular_deps]}}
@mcp.tool(annotations={"readOnlyHint": True})
async def estimate_module_tokens(
    module_name: Annotated[str | None, Field(description="Module name. None = all.")] = None,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Estimate token counts per module using line heuristics."""
    proj = await _proj(ctx, project_id)
    mods = await _db(ctx).get_modules(proj.id)
    if module_name:
        mods = [m for m in mods if m.name == module_name]
        if not mods: raise ToolError(f"Module '{module_name}' not found")
    lang = proj.languages[0] if proj.languages else "python"
    ests, total = [], 0
    for m in mods:
        t = estimate_tokens_from_lines(m.line_count, lang)
        ests.append({"module": m.name, "estimated_tokens": t, "line_count": m.line_count,
            "file_count": m.file_count, "language": lang})
        total += t
    return {"status": "success", "data": {"estimates": ests, "total_tokens": total}}
@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True})
async def create_analysis_plan(
    project_id: _Str = None,
    max_tokens_per_batch: Annotated[int,
        Field(description="Max tokens/batch.", ge=10000, le=200000)] = 60000,
    ctx: Context = None,
) -> dict:
    """Create analysis tasks ordered by DAG topology."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    mods_list = await db.get_modules(proj.id)
    snap = _parser(ctx).parse(proj.path)
    gr = build_dependency_graph(snap)
    gp = group_modules(gr.graph, snap)
    order = topological_order(gr.graph, gp.modules)
    lang = proj.languages[0] if proj.languages else "python"
    tasks, batches = [], []
    for bi, layer in enumerate(order):
        lt, lm = 0, []
        for mn in layer:
            mod = next((m for m in mods_list if m.name == mn), None)
            if not mod: continue
            t = estimate_tokens_from_lines(mod.line_count, lang)
            lt += t; lm.append(mn)
            tasks.append(AnalysisTask(id=f"task_{_uid()}", project_id=proj.id,
                module_name=mn, status="pending", batch_index=bi, created_at=_now()))
        if lm: batches.append({"batch": bi, "modules": lm, "estimated_tokens": lt})
    await db.create_tasks(tasks)
    tt = sum(b["estimated_tokens"] for b in batches)
    _budgets(ctx)[proj.id] = AnalysisBudgetController(
        total_budget=max(tt, 50000), total_modules=len(tasks))
    return {"status": "success",
        "summary": f"Created {len(tasks)} tasks in {len(batches)} layers",
        "data": {"tasks": batches, "total_batches": len(batches), "total_modules": len(tasks)}}
@mcp.tool(annotations={"readOnlyHint": True})
async def check_budget_status(project_id: _Str = None, ctx: Context = None) -> dict:
    """Check budget consumption and stop conditions."""
    proj = await _proj(ctx, project_id)
    ctrl = _budgets(ctx).get(proj.id)
    if ctrl is None:
        s = await _db(ctx).get_task_status_summary(proj.id)
        return {"status": "success", "data": {"total_budget": 0, "used_tokens": 0,
            "remaining_tokens": 0, "usage_percent": 0.0, "should_stop": False,
            "stop_reason": None, "task_summary": s}}
    return ctrl.check_budget_status(proj.id)
@mcp.tool(annotations={"readOnlyHint": True})
async def get_next_batch(
    project_id: _Str = None,
    batch_size: Annotated[int, Field(description="Max modules/batch.", ge=1, le=10)] = 3,
    ctx: Context = None,
) -> dict:
    """Get next pending modules to analyze."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    tasks = await db.get_next_pending_tasks(proj.id, batch_size)
    s = await db.get_task_status_summary(proj.id)
    batch = []
    for t in tasks:
        mod = await db.get_module(proj.id, t.module_name)
        batch.append({"name": t.module_name, "task_id": t.id,
            "files": mod.files if mod else [], "batch_index": t.batch_index})
    return {"status": "success", "data": {"modules": batch, "batch_count": len(batch),
        "progress_percent": s["progress_percent"], "remaining": s["pending"]}}
@mcp.tool(annotations={"readOnlyHint": False})
async def submit_analysis(
    module_name: Annotated[str, Field(description="Module name")],
    description: Annotated[str, Field(description="One-line module description")],
    public_interfaces: Annotated[list[str], Field(description="Public signatures")],
    key_data_structures: Annotated[list[str], Field(description="Key data structures")],
    dependencies: Annotated[list[str], Field(description="Dependencies")],
    patterns_identified: Annotated[list[str], Field(description="Design patterns")],
    detailed_analysis: Annotated[str | None,
        Field(description="Full Markdown analysis")] = None,
    mermaid_diagram: Annotated[str | None, Field(description="Mermaid diagram")] = None,
    token_count: Annotated[int, Field(description="Tokens consumed")] = 0,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Submit analysis results for a module and mark task completed."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    result = AnalysisResult(id=f"res_{_uid()}", task_id="", project_id=proj.id,
        module_name=module_name, description=description,
        public_interfaces=list(public_interfaces),
        key_data_structures=list(key_data_structures),
        dependencies=list(dependencies), dependents=[],
        patterns_identified=list(patterns_identified),
        detailed_analysis=detailed_analysis, mermaid_diagram=mermaid_diagram,
        token_count=token_count, created_at=_now())
    await db.insert_result(result)
    ctrl = _budgets(ctx).get(proj.id)
    if ctrl and token_count > 0:
        try: ctrl.allocate(module_name, token_count); ctrl.record_usage(module_name, token_count)
        except (ValueError, KeyError): pass
    s = await db.get_task_status_summary(proj.id)
    return {"status": "success",
        "summary": f"Analysis for '{module_name}' saved. {s['completed']}/{s['total']} done.",
        "data": {"result_id": result.id, "modules_completed": s["completed"],
            "modules_remaining": s["pending"], "progress_percent": s["progress_percent"]}}
@mcp.tool(annotations={"readOnlyHint": True})
async def get_analysis_status(project_id: _Str = None, ctx: Context = None) -> dict:
    """Get overall analysis progress: pending, in-progress, completed, failed."""
    s = await _db(ctx).get_task_status_summary((await _proj(ctx, project_id)).id)
    return {"status": "success", "data": {"total_tasks": s["total"], "pending": s["pending"],
        "in_progress": s["in_progress"], "completed": s["completed"], "failed": s["failed"],
        "completed_modules": s["completed_modules"], "progress_percent": s["progress_percent"]}}
@mcp.tool(annotations={"readOnlyHint": False})
async def save_checkpoint(
    phase: Annotated[Literal["indexing", "module_analysis", "cross_reference", "doc_generation"],
        Field(description="Current phase")],
    status: Annotated[Literal["in_progress", "completed", "interrupted"],
        Field(description="Status")] = "in_progress",
    tokens_processed: Annotated[int, Field(description="Tokens processed so far")] = 0,
    metadata: Annotated[dict | None, Field(description="Optional metadata")] = None,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Save analysis checkpoint for session resume."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    s = await db.get_task_status_summary(proj.id)
    mods = await db.get_modules(proj.id)
    analyzed, all_n = s["completed_modules"], [m.name for m in mods]
    pending = [n for n in all_n if n not in set(analyzed)]
    ckpt = await _ckpt(ctx).create_checkpoint(project_id=proj.id, phase=phase,
        analyzed_modules=analyzed, pending_modules=pending, status=status,
        total_tokens_processed=tokens_processed, metadata=metadata)
    pct = len(analyzed) / len(all_n) * 100 if all_n else 0.0
    return {"status": "success",
        "summary": f"Checkpoint: {len(analyzed)}/{len(all_n)} modules, phase={phase}",
        "data": {"checkpoint_id": ckpt.id, "analyzed_modules": analyzed,
            "pending_modules": pending, "progress_percent": round(pct, 1)}}
@mcp.tool(annotations={"readOnlyHint": True})
async def load_checkpoint(
    checkpoint_id: Annotated[str | None,
        Field(description="Checkpoint ID. None = latest.")] = None,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Load a checkpoint to resume a previous session."""
    proj = await _proj(ctx, project_id)
    restored = await _ckpt(ctx).restore_checkpoint(proj.id, checkpoint_id=checkpoint_id)
    if restored is None:
        return {"status": "success", "summary": "No checkpoint found", "data": None}
    ckpt, results = restored
    summaries = {r.module_name: {"description": r.description,
        "public_interfaces": r.public_interfaces, "token_count": r.token_count}
        for r in results}
    pct = len(ckpt.analyzed_modules) / ckpt.total_modules * 100 if ckpt.total_modules else 0.0
    return {"status": "success",
        "summary": f"Restored: {len(ckpt.analyzed_modules)}/{ckpt.total_modules} analyzed",
        "data": {"checkpoint_id": ckpt.id, "phase": ckpt.phase,
            "analyzed_modules": ckpt.analyzed_modules,
            "pending_modules": ckpt.pending_modules, "module_summaries": summaries,
            "progress_percent": round(pct, 1),
            "tokens_processed": ckpt.total_tokens_processed}}
@mcp.tool(annotations={"readOnlyHint": True})
async def get_cross_ref_context(
    module_name: Annotated[str, Field(description="Module being analyzed")],
    max_tokens: Annotated[int,
        Field(description="Max tokens for context.", ge=500, le=30000)] = 2000,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Build cross-reference context from dependency summaries, trimmed to max_tokens."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    mod = await db.get_module(proj.id, module_name)
    if mod is None: raise ToolError(f"Module '{module_name}' not found")
    all_res = await db.get_all_results(proj.id)
    parts, resolved, tok_est = [], 0, 0
    for r in all_res:
        if r.module_name == module_name: continue
        entry = f"# {r.module_name}\n{r.description}\nInterfaces: {', '.join(r.public_interfaces[:10])}\n---\n"
        et = len(entry) // 4
        if tok_est + et > max_tokens: break
        parts.append(entry); tok_est += et; resolved += 1
    pending = max(0, len(await db.get_modules(proj.id)) - 1 - resolved)
    return {"status": "success", "data": {"target_module": module_name,
        "context": "\n".join(parts), "dependencies_resolved": resolved,
        "dependencies_pending": pending, "context_tokens": tok_est}}
@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True})
async def plan_doc_structure(project_id: _Str = None, ctx: Context = None) -> dict:
    """Plan documentation tree: depths, splits, budgets per module."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    mods = await db.get_modules(proj.id)
    snap = _parser(ctx).parse(proj.path)
    gr = build_dependency_graph(snap)
    gp = group_modules(gr.graph, snap)
    metrics = get_module_metrics(gr.graph, gp.modules)
    plan = _plan_doc_structure(proj.id, mods, metrics)
    nodes = [DocNode(id=f"doc_{_uid()}", project_id=proj.id, path=n.path,
        level=n.level, target=n.target, token_budget=n.token_budget,
        parent_path=n.parent_path, children_paths=list(n.children_paths),
        status="planned") for n in plan.doc_tree]
    await db.insert_doc_nodes(nodes)
    tree = [{"path": n.path, "level": n.level, "target": n.target,
        "token_budget": n.token_budget, "parent": n.parent_path,
        "children": list(n.children_paths)} for n in plan.doc_tree]
    return {"status": "success",
        "summary": f"Planned {plan.total_docs} docs, max depth {plan.max_depth}",
        "data": {"doc_tree": tree, "total_docs": plan.total_docs,
            "max_depth": plan.max_depth, "depth_decisions": plan.depth_decisions}}
@mcp.tool(annotations={"readOnlyHint": False})
async def generate_doc(
    target: Annotated[str, Field(description="Module name or 'root' for INDEX")],
    level: Annotated[int, Field(description="0=INDEX, 1=OVERVIEW, 2+=DETAIL", ge=0, le=5)],
    token_budget: Annotated[int, Field(description="Token budget", ge=200)],
    parent_path: Annotated[str | None, Field(description="Parent doc path")] = None,
    children: Annotated[list[str] | None, Field(description="Child doc paths")] = None,
    project_id: _Str = None, ctx: Context = None,
) -> dict:
    """Generate a single Jinja2-rendered document for a target at a given level."""
    db, proj = _db(ctx), await _proj(ctx, project_id)
    res = await db.get_result(proj.id, target) if target != "root" else None
    all_res = await db.get_all_results(proj.id)
    xref = "\n".join(f"## {r.module_name}\n{r.description}" for r in all_res
                     if r.module_name != target)[:5000]
    csums: list[dict] = []
    if children:
        dtree = await db.get_doc_tree(proj.id)
        for cp in children:
            cn = next((n for n in dtree if n.path == cp), None)
            if cn:
                cr = await db.get_result(proj.id, cn.target)
                csums.append({"name": cn.target, "path": cn.path, "level": cn.level,
                    "description": cr.description if cr else cn.target})
    dp = ("INDEX.md" if level == 0 else f"{target}/OVERVIEW.md" if level == 1
          else f"{target}/DETAIL.md")
    node = DocNode(id=f"doc_{_uid()}", project_id=proj.id, path=dp, level=level,
        target=target, token_budget=token_budget, parent_path=parent_path,
        children_paths=children or [], status="planned")
    gen = _docgen(ctx).generate_doc(node=node, analysis_result=res,
        cross_ref_context=xref, children_summaries=csums)
    await db.update_doc_node_content(node.id, gen.content, gen.actual_tokens)
    return {"status": "success", "data": {"path": gen.path, "content": gen.content,
        "actual_tokens": gen.actual_tokens, "level": gen.level, "target": gen.target}}

if __name__ == "__main__":
    mcp.run()
