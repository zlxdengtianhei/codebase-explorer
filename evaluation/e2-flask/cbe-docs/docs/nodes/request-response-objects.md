# Request and Response Wrappers

**Capability.** Owns Flask's Request and Response classes: routing metadata on the request (endpoint, blueprint chain, url_rule), per-request and config-derived limits (max_content_length, max_form_memory_size, max_form_parts, max_cookie_size), and JSON failure handling.

Use this to understand what extra state Flask attaches to Werkzeug's request/response and how limits resolve per-request versus from app config. Request.blueprints uses helpers._split_blueprint_path for the parent chain.

**Depends on.**

- [Shared Helpers](helpers-utilities.md) · model-inferred · 0 edge(s)

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
