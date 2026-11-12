#!/usr/bin/env python3
"""Build exact Flask source excerpts and catalog tree data for the code film."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


APP = "src/flask/app.py::method::Flask."
CTX = "src/flask/ctx.py::method::RequestContext."
BP = "src/flask/sansio/blueprints.py::method::Blueprint."
CONFIG = "src/flask/config.py::method::Config."

# Each view corresponds to one spoken sentence. Block ranges stay inside the
# catalog unit ranges named by `units`; globals.py is checked against source only.
SCENES = {
    "1": {
        "title": "Enter through wsgi_app",
        "views": [
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "blocks": [("src/flask/app.py", 1505, 1513, [1505, 1507, 1508])]},
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "blocks": [("src/flask/app.py", 1514, 1527, [1514, 1526])]},
        ],
    },
    "2": {
        "title": "Push the request context",
        "views": [
            {"node": "app-and-request-context-management", "units": [CTX + "push::12063"], "blocks": [("src/flask/ctx.py", 367, 390, list(range(370, 379)) + [385, 386, 389, 390])]},
            {"node": "app-and-request-context-management", "units": [CTX + "match_request::11664"], "blocks": [("src/flask/ctx.py", 357, 365, [361, 362])]},
        ],
    },
    "3": {
        "title": "Run the full dispatch cycle",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "full_dispatch_request::36613"], "blocks": [("src/flask/app.py", 904, 920, [911, 913, 914])]},
            {"node": "request-dispatch-cycle", "units": [APP + "full_dispatch_request::36613"], "blocks": [("src/flask/app.py", 904, 920, [914, 915, 916, 920])]},
        ],
    },
    "4": {
        "title": "Before-request hooks",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "preprocess_request::51235"], "blocks": [("src/flask/app.py", 1271, 1296, [1282, 1288, 1289, 1290, 1291])]},
            {"node": "request-dispatch-cycle", "units": [APP + "preprocess_request::51235"], "blocks": [("src/flask/app.py", 1271, 1296, [1291, 1292, 1293, 1294])]},
        ],
    },
    "5": {
        "title": "Resolve and call the view",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "dispatch_request::35345"], "blocks": [("src/flask/app.py", 879, 902, [890, 891, 892, 901, 902])]},
        ],
    },
    "6": {
        "title": "Make a response",
        "views": [
            {"node": "response-finalization-and-error-fallback", "units": [APP + "finalize_request::37229"], "blocks": [("src/flask/app.py", 939, 951, [939, 941])]},
            {"node": "response-finalization-and-error-fallback", "units": [APP + "make_response::45351"], "blocks": [("src/flask/app.py", 1214, 1233, [1215, 1216, 1223, 1228, 1229])]},
        ],
    },
    "7": {
        "title": "After-request work and teardown",
        "views": [
            {"node": "response-finalization-and-error-fallback", "units": [APP + "process_response::52366"], "blocks": [("src/flask/app.py", 1310, 1324, list(range(1311, 1323)))]},
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "blocks": [("src/flask/app.py", 1514, 1527, [1517, 1526])]},
        ],
    },
    "8": {
        "title": "What the two contexts hold",
        "views": [
            {"node": "app-and-request-context-management", "units": ["grp:ctx.py-appcontext"], "sourceOnly": True, "blocks": [("src/flask/ctx.py", 238, 253, [246, 247, 248, 249])]},
            {"node": "app-and-request-context-management", "units": ["src/flask/ctx.py::class::RequestContext::8798::s0", CTX + "__init__::9823"], "blocks": [("src/flask/ctx.py", 309, 335, [317, 319, 321, 323, 325, 326, 327, 331])]},
        ],
    },
    "9": {
        "title": "Proxies find the active objects",
        "views": [
            {"node": "app-and-request-context-management", "units": [], "blocks": [("src/flask/globals.py", 24, 32, [24, 28, 29]), ("src/flask/globals.py", 42, 50, [42, 46, 47])]},
            {"node": "app-and-request-context-management", "units": [], "blocks": [("src/flask/globals.py", 24, 32, [28, 29]), ("src/flask/globals.py", 42, 50, [46, 47])]},
        ],
    },
    "10": {
        "title": "Blueprints defer registration",
        "views": [
            {"node": "blueprint-deferred-registration", "units": [BP + "record::8831", BP + "add_url_rule::16654"], "blocks": [("src/flask/sansio/blueprints.py", 223, 230, [230]), ("src/flask/sansio/blueprints.py", 423, 441, [432, 433, 434])]},
            {"node": "blueprint-deferred-registration", "units": [BP + "register::10928"], "blocks": [("src/flask/sansio/blueprints.py", 327, 345, [334, 335, 337, 338])]},
        ],
    },
    "11": {
        "title": "Load configuration",
        "views": [
            {"node": "configuration-loading", "units": [CONFIG + "from_pyfile::6295", CONFIG + "from_object::7574"], "blocks": [("src/flask/config.py", 202, 216, [202, 203, 204, 205, 215]), ("src/flask/config.py", 245, 254, [246, 252, 253, 254])]},
            {"node": "configuration-loading", "units": [CONFIG + "from_prefixed_env::4172"], "blocks": [("src/flask/config.py", 150, 166, [153, 154, 157, 158, 161, 162, 163]), ("src/flask/config.py", 168, 180, [168, 170, 171, 174, 175, 177, 178, 180])]},
        ],
    },
}

TOPS = [
    "runtime-app-contexts-and-testing",
    "sansio-app-and-scaffold-foundations",
    "templates-views-and-wrappers",
    "session-interface-and-cookies",
    "configuration-loading",
    "json-providers-and-helpers",
    "tagged-json-serialization",
    "command-line-and-public-helpers",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with gzip.open(args.catalog, "rt", encoding="utf-8") as f:
        catalog = json.load(f)
    script = json.loads(args.script.read_text(encoding="utf-8"))
    assert set(SCENES) == {item["id"] for item in script["items"]}
    source_cache = {}
    output_items = []

    for item in script["items"]:
        spec = SCENES[item["id"]]
        sentence_count = len([s for s in re.split(r"(?<=[.!?])\s+", item["caption"]) if s])
        assert sentence_count == len(spec["views"]), (item["id"], sentence_count)
        views = []
        for view in spec["views"]:
            node = view["node"]
            assert node in catalog["nodes"]
            ranges = []
            for unit_id in view["units"]:
                unit = catalog["units"][unit_id]
                assert unit["node"] == node, (unit_id, node)
                for r in unit["ranges"]:
                    ranges.extend((r["path"], a, b) for a, b in r["lines"])
            blocks = []
            for path, first, last, highlights in view["blocks"]:
                if ranges and not view.get("sourceOnly"):
                    assert any(path == p and a <= first and last <= b for p, a, b in ranges), (item["id"], path, first, last)
                assert first <= last and set(highlights) <= set(range(first, last + 1))
                if path not in source_cache:
                    disk = args.source_root / path
                    raw = disk.read_bytes()
                    source_cache[path] = {
                        "lines": raw.decode("utf-8").splitlines(),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                source = source_cache[path]["lines"]
                assert last <= len(source)
                blocks.append({
                    "path": path,
                    "first": first,
                    "last": last,
                    "highlights": highlights,
                    "lines": source[first - 1:last],
                    "sha256": source_cache[path]["sha256"],
                })
            primary = view["units"][0] if view["units"] else None
            views.append({
                "node": node,
                "unit": catalog["units"][primary]["signature"] if primary else "current_app / request",
                "unitId": primary,
                "blocks": blocks,
            })
        output_items.append({**item, "title": spec["title"], "views": views})

    nodes = {k: {key: catalog["nodes"][k][key] for key in ("title", "parent", "children", "capability")} for k in catalog["nodes"]}
    result = {
        "name": "Flask",
        "sourceRevision": "85c5d93cbd049c4bd0679c36fd1ddcae8c37b642",
        "tops": TOPS,
        "nodes": nodes,
        "items": output_items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(output_items)} narration items, {sum(len(i['views']) for i in output_items)} source views")


if __name__ == "__main__":
    main()
