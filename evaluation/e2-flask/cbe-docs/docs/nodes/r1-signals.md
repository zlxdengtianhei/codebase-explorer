# Blinker Signals

**Capability.** Definition of Flask's ten named lifecycle signals on a private blinker Namespace; the module is pure declaration with no behavioral logic.

Use this as the reference for signal names available for subscription (request_started, appcontext_popped, message_flashed, etc.). Emission points live in the dispatch, templating, and flashing code.

Parent: [Flask Framework](r1-flask-framework.md)

## Units (1)

<a id="u-2c78c6c4455c"></a>
### `signals.py module code (L1–L17)`

`module_region` · [src/flask/signals.py:L1-L17][f1]

No behavioral logic: creates a private blinker Namespace for Flask's own signals and defines ten named signals (template_rendered, before_render_template, request_started, request_finished, request_tearing_down, got_request_exception, appcontext_tearing_down, appcontext_pushed, appcontext_popped, message_flashed) via _signals.signal(...).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/signals.py
