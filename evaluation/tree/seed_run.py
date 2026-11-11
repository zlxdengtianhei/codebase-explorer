"""Make a run whose detail is already settled, from a published catalog, without spending model calls on detail.

Evaluation tool, not part of the installed package. It plans a real run on a checkout of the
repository the catalog describes, writes every reading batch's accepted answer from the catalog's
units and dispositions, and seeds the aggregation cache with the catalog's units and their rolled-up
edges (the catalog does not keep the analyzer graph, so the cache is where the resolved edges come
from). Units whose ids the current inventory no longer has are dropped, and inventory ids the catalog never
covered are indexed without prose; both counts are printed. The tree tasks then run through the real state machine, for example:

    python -m cbe generate CHECKOUT --resume --run-dir RUN --model MODEL --base-url URL ...

The run reads a copy of the checkout that holds only the files the catalog inventories (the original
runs covered a subset of the repository), and each copied file must match the catalog's SHA-256.

usage: python seed_run.py CATALOG.json.gz CHECKOUT RUN_DIR NAME   (NAME is the repository's name on the entry page)
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path

from cbe import aggregation, host_run, symbols

UNIT_FIELDS = ("id", "kind", "members", "explain", "summary", "extras", "relations", "uncertainties")


def subset(catalog: dict, checkout: Path, dest: Path) -> Path:
    """Copy the inventoried files of the checkout; fail when one differs from the catalog's digest."""
    for path, row in catalog["inventory"].items():
        raw = (checkout / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise SystemExit(f"{path} differs from the catalog's digest: wrong checkout")
        (dest / path).parent.mkdir(parents=True, exist_ok=True)
        (dest / path).write_bytes(raw)
    return dest


def seed(catalog_path: Path, checkout: Path, run_dir: Path, name: str, *, jobs: int = 2) -> dict:
    catalog = json.load(gzip.open(catalog_path))
    work = run_dir.parent / "source" / name
    shutil.rmtree(work, ignore_errors=True)
    plan = host_run.plan(subset(catalog, checkout, work), run_dir, review="none", jobs=jobs, host="api",
                         driver="script")
    run_dir = Path(plan["run_dir"])
    units = catalog["units"]
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    module_of = {path: row["number"] for row in state["modules"] for path in row["files"]}

    def home(unit: dict) -> int | None:
        for rng in unit.get("ranges") or []:
            if rng["path"] in module_of:
                return module_of[rng["path"]]
        return module_of.get(unit["id"].split("::", 1)[0])

    inventory_ids = set(symbols.inventory_ids(state["inventory"]))
    outputs = {row["number"]: {"units": [], "dispositions": {}} for row in state["modules"]}
    dropped, kept = [], {}
    for uid, unit in units.items():
        number = home(unit)
        members = unit.get("members") or []
        # The catalog may come from an older context builder: a unit whose ids the current inventory lacks is dropped.
        if number is None or not (set(members) <= inventory_ids if unit["kind"] == "group" else uid in inventory_ids):
            dropped.append(uid)
            continue
        kept[uid] = unit
        outputs[number]["units"].append({k: unit[k] for k in UNIT_FIELDS if k in unit})
    for key, entry in catalog["dispositions"].items():
        number = module_of.get(key.split("::", 1)[0])
        if number is not None and key in inventory_ids and (entry.get("unit") is None or entry["unit"] in kept):
            outputs[number]["dispositions"][key] = entry
    filled = 0
    for key in sorted(inventory_ids):
        number = module_of.get(key.split("::", 1)[0])
        if number is not None and key not in outputs[number]["dispositions"]:
            outputs[number]["dispositions"][key] = {"how": "index_only", "unit": None,
                                                    "reason": "the replayed catalog has no unit for this id"}
            filled += 1
    with host_run.locked_state(run_dir) as live:
        for number, output in outputs.items():
            task = live["tasks"][f"module_{number + 1}"]
            if not output["units"] and not output["dispositions"]:
                continue   # a batch of empty files: the state machine completes it itself
            host_run.write_json(host_run.state_dir(run_dir) / "accepted" / f"{task['id']}.json", output)
            task["status"], task["output"], task["attempts"] = "done", f"host/accepted/{task['id']}.json", 1
        fingerprint = host_run._detail_fingerprint(run_dir, live)
        records = kept
        edges = aggregation.unit_edges(records, catalog["edges"])
        raw = json.dumps({"fingerprint": fingerprint, "records": records, "edges": edges},
                         ensure_ascii=False).encode("utf-8")
        cache = host_run.state_dir(run_dir) / "aggregation-inputs.json"
        cache.write_bytes(raw)
        live["aggregation_cache"] = {"fingerprint": fingerprint, "content_digest": hashlib.sha256(raw).hexdigest()}
    return {"run_dir": str(run_dir), "source": str(work), "catalog_units": len(units), "units": len(kept),
            "dropped_units": len(dropped), "index_only_filled": filled, "edges": len(edges),
            "modules": len(outputs)}


if __name__ == "__main__":
    print(json.dumps(seed(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]), indent=2))
