"""Small CLI for reproducible Variant C evidence runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .incremental import file_revisions_from_repo
from .pipeline import VariantCPipeline, save_pipeline_evidence
from .producer import Invocation, RouterInvoker
from .models import BatchPlan


class FailingInvoker:
    def invoke(self, prompt: str, *, task_name: str) -> Invocation:
        raise RuntimeError("LLM disabled by --no-llm; deterministic residual is required")


class DeterministicInvoker:
    """A local proof producer; it exercises the real submit/render gates."""

    def invoke(self, prompt: str, *, task_name: str) -> Invocation:
        candidate_section = prompt.split("Candidates（封闭集合）：", 1)[-1]
        candidate_lines = [
            line for line in candidate_section.splitlines() if line.startswith("- ") and ": " in line
        ]
        candidate_ids = [line[2:].rsplit(": ", 1)[0].strip() for line in candidate_lines]
        candidate = next((item for item in candidate_ids if not item.startswith("page:")), candidate_ids[0] if candidate_ids else "")
        body = (
            "## 初始化\n确定层已将本批次文件卡按功能簇归档。\n"
            "## 请求流程\n本批次的请求关系只引用输入边和符号卡。\n"
            "## 响应阶段\n表达页保留四节结构，并由渲染器生成锚点。\n"
            "## 异常处理\n未在此层补写源码之外的运行时推断。\n"
        )
        return Invocation(
            text=json.dumps(
                {
                    "body": body,
                    "selected_target_ids": [candidate] if candidate else [],
                    "covered_symbol_ids": [],
                },
                ensure_ascii=False,
            ),
            provider="deterministic-proof",
        )


def _load_clusters(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("clusters JSON must be an object")
    return value


def _cluster_config(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    raw = _load_clusters(path)
    if "cluster_by_file" in raw:
        mapping = raw.get("cluster_by_file")
        if not isinstance(mapping, dict):
            raise ValueError("cluster_by_file must be an object")
        return (
            {str(key): str(value) for key, value in mapping.items()},
            {str(key): str(value) for key, value in (raw.get("cluster_names") or {}).items()},
            {str(key): str(value) for key, value in (raw.get("cluster_purposes") or {}).items()},
        )
    return ({str(key): str(value) for key, value in raw.items()}, {}, {})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--clusters", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--public-surface", default=None)
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--router-python", default=None)
    parser.add_argument(
        "--router-workdir",
        default=None,
        help="context-infra root used to import and run the repository router",
    )
    parser.add_argument(
        "--router-timeout",
        type=int,
        default=240,
        help="per-tier router progress timeout in seconds",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    cluster_by_file, names, purposes = _cluster_config(Path(args.clusters))
    public_surface: dict[str, str | None] = {}
    if args.public_surface:
        surface = json.loads(Path(args.public_surface).read_text(encoding="utf-8"))
        binding_targets = {
            str(item.get("name")): tuple(item.get("resolved_symbol_ids") or ())
            for item in (surface.get("bindings") or [])
            if isinstance(item, dict) and item.get("name")
        }
        for name in surface.get("exported_names") or []:
            hits = binding_targets.get(str(name), ())
            public_surface[str(name)] = hits[0] if len(hits) == 1 else None
    file_paths = ledger.get("files") if isinstance(ledger, dict) else {}
    revisions = file_revisions_from_repo(repo, file_paths or {})
    if args.no_llm:
        invoker = FailingInvoker()
    elif args.deterministic:
        invoker = DeterministicInvoker()
    else:
        invoker = RouterInvoker(
            workdir=repo,
            python_executable=args.router_python,
            router_workdir=args.router_workdir,
            router_timeout_seconds=args.router_timeout,
            timeout_seconds=args.router_timeout + 30,
        )
    pipeline = VariantCPipeline.from_file_clusters(
        ledger,
        cluster_by_file=cluster_by_file,
        cluster_names=names,
        cluster_purposes=purposes,
        file_revisions=revisions,
        invoker=invoker,
        public_surface=public_surface,
    )
    result = pipeline.run(output_dir=args.out)
    save_pipeline_evidence(result, args.receipt)
    print(json.dumps(result.metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
