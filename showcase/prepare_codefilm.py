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
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "blocks": [("src/flask/app.py", 1506, 1511, [1506])]},
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "blocks": [("src/flask/app.py", 1506, 1511, [1506, 1510, 1511]), ("src/flask/app.py", 1518, 1527, [1518, 1519, 1527])]},
        ],
    },
    "2": {
        "title": "Push the request context",
        "views": [
            {"node": "app-and-request-context-management", "units": [CTX + "push::12063"], "blocks": [("src/flask/ctx.py", 367, 394, [372, 373, 374, 384, 385, 386, 393, 394])]},
            {"node": "app-and-request-context-management", "units": [CTX + "match_request::11664"], "blocks": [("src/flask/ctx.py", 357, 365, [363])]},
        ],
    },
    "3": {
        "title": "Run the full dispatch cycle",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "full_dispatch_request::36613"], "blocks": [("src/flask/app.py", 904, 920, [914, 915])]},
            {"node": "request-dispatch-cycle", "units": [APP + "full_dispatch_request::36613"], "blocks": [("src/flask/app.py", 904, 920, [915, 916, 917])]},
        ],
    },
    "4": {
        "title": "Before-request hooks",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "preprocess_request::51235"], "blocks": [("src/flask/app.py", 1271, 1296, [1281, 1288, 1289, 1290, 1291])]},
            {"node": "request-dispatch-cycle", "units": [APP + "preprocess_request::51235"], "blocks": [("src/flask/app.py", 1271, 1296, [1293, 1294])]},
        ],
    },
    "5": {
        "title": "Resolve and call the view",
        "views": [
            {"node": "request-dispatch-cycle", "units": [APP + "dispatch_request::35345"], "blocks": [("src/flask/app.py", 879, 902, [892, 901, 902])]},
        ],
    },
    "6": {
        "title": "Make a response",
        "views": [
            {"node": "response-finalization-and-error-fallback", "units": [APP + "finalize_request::37229"], "blocks": [("src/flask/app.py", 939, 951, [939])]},
            {"node": "response-finalization-and-error-fallback", "units": [APP + "make_response::45351"], "blocks": [("src/flask/app.py", 1219, 1232, [1220, 1224, 1225, 1226, 1227, 1230, 1231])]},
        ],
    },
    "7": {
        "title": "After-request work and teardown",
        "views": [
            {"node": "response-finalization-and-error-fallback", "units": [APP + "process_response::52366"], "blocks": [("src/flask/app.py", 1311, 1324, [1313, 1314, 1316, 1319, 1321, 1322])]},
            {"node": "wsgi-entry-and-request-contexts", "units": [APP + "wsgi_app::59470"], "sourceOnly": True,
             "label": "Flask.wsgi_app · RequestContext.pop",
             "blocks": [("src/flask/app.py", 1518, 1527, [1519, 1527]), ("src/flask/ctx.py", 404, 410, [410])]},
        ],
    },
    "8": {
        "title": "What the two contexts hold",
        "views": [
            {"node": "app-and-request-context-management", "units": ["grp:ctx.py-appcontext"], "sourceOnly": True, "blocks": [("src/flask/ctx.py", 238, 253, [246, 247, 248])]},
            {"node": "app-and-request-context-management", "units": ["src/flask/ctx.py::class::RequestContext::8798::s0", CTX + "__init__::9823"], "blocks": [("src/flask/ctx.py", 309, 335, [320, 323, 325, 326, 327, 331])]},
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
            {"node": "blueprint-deferred-registration", "units": [BP + "record::8831", BP + "add_url_rule::16654"], "blocks": [("src/flask/sansio/blueprints.py", 223, 230, [230]), ("src/flask/sansio/blueprints.py", 412, 420, [413]), ("src/flask/sansio/blueprints.py", 433, 441, [433, 434, 435, 436, 437, 438, 439])]},
            {"node": "blueprint-deferred-registration", "units": [BP + "register::10928", "grp:blueprints.py-merge-blueprint-funcs"],
             "label": "Blueprint.register · Blueprint._merge_blueprint_funcs",
             "blocks": [("src/flask/sansio/blueprints.py", 330, 335, [331, 332, 334, 335]), ("src/flask/sansio/blueprints.py", 399, 403, [399, 400, 402, 403])]},
        ],
    },
    "11": {
        "title": "Load configuration",
        "views": [
            {"node": "configuration-loading", "units": [CONFIG + "from_pyfile::6295", CONFIG + "from_object::7574", CONFIG + "from_mapping::10951", CONFIG + "from_file::9243", CONFIG + "from_prefixed_env::4172"], "blocks": [("src/flask/config.py", 187, 189, [187, 188, 189]), ("src/flask/config.py", 218, 218, [218]), ("src/flask/config.py", 304, 306, [304, 305, 306]), ("src/flask/config.py", 256, 261, [256, 257, 258, 259, 260, 261]), ("src/flask/config.py", 126, 128, [126, 127, 128])]},
            {"node": "configuration-loading", "units": [CONFIG + "from_prefixed_env::4172", CONFIG + "from_object::7574"], "blocks": [("src/flask/config.py", 252, 254, [252, 253, 254]), ("src/flask/config.py", 158, 165, [158, 159, 161, 162]), ("src/flask/config.py", 172, 185, [173, 174, 176, 178, 179, 181, 183])]},
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
    invalid_highlights = []
    highlight_count = 0

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
            # Excerpts read top to bottom: in file order, then line order.
            for path, first, last, highlights in sorted(view["blocks"], key=lambda b: (b[0], b[1])):
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
                for line_number in highlights:
                    stripped = source[line_number - 1].strip()
                    if (not stripped or stripped.startswith("#")
                            or re.fullmatch(r"[\"'()\[\]{}:,]+", stripped)):
                        invalid_highlights.append(f"{path}:{line_number}: {stripped!r}")
                highlight_count += len(highlights)
                blocks.append({
                    "path": path,
                    "first": first,
                    "last": last,
                    "highlights": highlights,
                    "lines": source[first - 1:last],
                    "sha256": source_cache[path]["sha256"],
                })
            primary = view["units"][0] if view["units"] else None
            # A view that shows several units names each of them, in source order, instead of
            # putting all excerpts under the first unit's signature.
            def first_line(uid):
                ranges = catalog["units"][uid].get("ranges") or [{"path": "", "lines": [[0, 0]]}]
                return (ranges[0]["path"], ranges[0]["lines"][0][0])
            label = view.get("label") or (catalog["units"][primary]["signature"] if len(view["units"]) == 1 else
                     " · ".join(uid.split("::")[2] if uid.count("::") >= 2 else uid.removeprefix("grp:")
                                for uid in sorted(view["units"], key=first_line))
                     if view["units"] else "current_app / request")
            views.append({
                "node": node,
                "unit": label,
                "unitId": primary,
                "blocks": blocks,
            })
        output_items.append({**item, "title": spec["title"], "views": views})

    if invalid_highlights:
        details = "\n".join(invalid_highlights)
        raise SystemExit(f"invalid highlighted source lines: {len(invalid_highlights)}\n{details}")
    print(f"highlight validation: {highlight_count} highlighted lines, 0 invalid")

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
