"""Codebase Explorer semantic documentation product."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("codebase-explorer")
except PackageNotFoundError:
    # Source checkout without installed distribution metadata.
    __version__ = "source"


AGENTS_MD_NOTE = ("Paste these three lines into this repository's AGENTS.md or CLAUDE.md; "
                  "agents that work here later will read the map first.")


def agents_md_lines(run_dir: str | None = None) -> list[str]:
    """Three lines that point a repository's later agents at its map; repository-relative paths only.

    Without ``run_dir`` (printed at install time, before any run) the lines say to put the
    newest run's directory name in place of NEWEST, and ``cbe stale`` finds the latest run itself.
    """
    newest = "the newest directory under `.codebase-analysis/runs/`"
    if run_dir:
        where, run = f"`{run_dir}` (if it is gone, {newest})", run_dir
        stale = f"cbe stale --repo . --run-dir {run_dir}"
        fill = ""
    else:
        where, run = newest + ", here called NEWEST", ".codebase-analysis/runs/NEWEST"
        stale = "cbe stale --repo ."
        fill = " Replace NEWEST with that directory's name."
    return [f"This repository has a Codebase Explorer map in {where}. Before you search the code, "
            f"read its `docs/INDEX.md`, then the module page that fits the task.{fill}",
            f"Get exact facts with `cbe find --run-dir {run} NAME`, then `cbe query` and `cbe source` "
            f"with the same `--run-dir`.{fill} Where an explanation and the source disagree, the source is right.",
            f"`{stale}` lists the pages that describe code changed after the map was made; "
            "for those, read the source."]
