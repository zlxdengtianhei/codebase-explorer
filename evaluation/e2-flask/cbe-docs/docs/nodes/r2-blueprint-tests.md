# Blueprint Test Suite

**Capability.** Pins blueprint behavior: error-handler scoping, endpoint naming, URL prefixes/defaults/processors, context processors, template filters/tests/globals, nesting and callback ordering, static max-age overrides, and registration-name rules.

Read these to confirm scoping and naming semantics, including that blueprint static max-age overrides app config and that re-registration and self-registration raise ValueError. The templates/static tests verify loader merging.

**Depends on.**

- [App-Scope Blueprint Hooks](r2-blueprint-app-integrations.md) · model-inferred · 0 edge(s)
- [Blueprint Registration](r2-blueprint-registration.md) · model-inferred · 0 edge(s)
- [Concrete Blueprint Runtime](r2-blueprint-runtime.md) · model-inferred · 0 edge(s)
- [Testing Support](r2-testing-support.md) · model-inferred · 0 edge(s)

Parent: [Blueprint System](r2-blueprint-system.md)

## Units (18)

<a id="u-0a599a4fdcef"></a>
### `test-blueprints-context-processing`

`def test_context_processing(app, client):` · [tests/test_blueprints.py:L634-L637][f1]

test_context_processing distinguishes blueprint-local and app-wide context processors.

answer_bp.app_context_processor injects notanswer=43 app-wide; answer_bp.context_processor injects answer=42 only for the blueprint's own endpoints. Both the app route '/' and blueprint route '/bp' render the same template string; the app page contains 43 but not 42, while the blueprint page contains both 42 and 43, demonstrating that blueprint-local processors do not affect app endpoints.

imports: [test_blueprints.py module code (L1–L7)][f1]

<a id="u-a07314bd4116"></a>
### `test-blueprints-endpoints`

`def test_dotted_name_not_allowed(app, client):` · [tests/test_blueprints.py:L254-L256][f1]

These tests cover endpoint naming and name validation.

test_dotted_name_not_allowed and test_empty_name_not_allowed assert ValueError from flask.Blueprint for dotted and empty names. test_dotted_names_from_app shows an app route reversing to a blueprint endpoint via url_for('test.index') yielding '/test/'. test_route_decorator_custom_endpoint shows endpoints default to blueprint-qualified view names (bp.foo, bp.bar_foo) and can be overridden with endpoint='bar' or '123' (allowing digits). test_route_decorator_custom_endpoint_with_dots asserts ValueError for endpoint 'a.b' whether passed to bp.route, bp.add_url_rule, or derived from view.__name__. test_endpoint_decorator binds a view to a pre-added url_map Rule with endpoint 'bar'; /foo resolves to it, while the blueprint-prefixed /bp_prefix/bar 404s.

**Uncertainties.**

- Whether the endpoint decorator path validates endpoint names identically to route/add_url_rule is asserted only indirectly

<a id="u-d5325e814ca1"></a>
### `test-blueprints-error-handling`

`def test_blueprint_specific_error_handling(app, client):` · [tests/test_blueprints.py:L8-L13][f1]

These tests verify error-handler scoping for blueprints.

test_blueprint_specific_error_handling registers frontend/backend/sideend blueprints: a 403 abort inside a blueprint that has errorhandler(403) returns that blueprint's own body ('frontend says no'/'backend says no'); an abort on the sideend, which registers no handler, falls back to the app-level errorhandler registered after the blueprints ('application itself says no'). test_blueprint_specific_user_error_handling shows exception-class handlers: @blue.errorhandler(MyDecoratorException) and blue.register_error_handler(MyFunctionException, fn) both dispatch only on matching exception type, returning 'boom'/'bam'. test_blueprint_app_error_handling shows @errors.app_errorhandler(403) applying app-wide: it handles 403s from both a plain app route (/forbidden) and a different blueprint's route (/nope), both returning 'you shall not pass'.

imports: [test_blueprints.py module code (L1–L7)][f1]; group: [test-blueprints-url-and-routing](../../catalog.json), [test-blueprints-url-processors](r2-blueprint-tests.md#u-01cb4f929d78)

**Uncertainties.**

- Full handler-precedence order for nested blueprints is only observed for these specific cases, not systematically characterized from this source

<a id="u-8ffa01bc1cec"></a>
### `test-blueprints-nesting`

`def test_nested_blueprint(app, client):` · [tests/test_blueprints.py:L793-L798][f1]

These tests cover nested blueprints and their prefixes, subdomains, and callback ordering.

test_nested_blueprint nests child into parent and grandchild into child with url_prefixes /child and /grandchild under parent's /parent; routes resolve at the concatenated prefixes, and 403 aborts are handled by the nearest blueprint errorhandler: /parent/no and /parent/child/no both yield 'Parent no' (parent's handler), /parent/child/grandchild/no yields 'Grandchild no'. test_nested_callback_order registers before_request handlers on app, parent, child each appending two entries; /a returns 'app_1, app_2, parent_1, parent_2, child_1, child_2' (outer-to-inner before-request order, mirrored by teardown pop assertions), and /b renders {{ key }} as 'child', showing the innermost context_processor wins. test_nesting_url_prefixes is parametrized over four combinations of url_prefix set at init vs registration time, all producing a matching /parent/child/ route (200). test_nesting_subdomains registers a nested blueprint under subdomain 'api' with SERVER_NAME set and subdomain_matching enabled; /child/ on api.example.test returns 200. test_child_and_parent_subdomain sets the subdomain on the child instead; / resolves on api.parent.example.test (200) but 404s on parent.example.test.

**Uncertainties.**

- How the effective subdomain combines when both child and parent set one (the child-only case shows the child's value used with the parent prefix) is inferred from assertions only

<a id="u-1022e367e59b"></a>
### `test-blueprints-prefix-slash`

`def test_blueprint_prefix_slash(app, client, prefix, rule, url):` · [tests/test_blueprints.py:L104-L123][f1]

test_blueprint_prefix_slash is parametrized over eleven (prefix, rule, url) combinations and asserts that empty prefixes, missing or doubled trailing and leading slashes all normalize so each expected URL matches the single registered route, answered with an empty 204 response.

The slash-merging itself happens in routing code not shown here; only the expectations are observable.

**Uncertainties.**

- The normalization algorithm lives in werkzeug routing; only input/output pairs are observed

<a id="u-74393a252d63"></a>
### `test-blueprints-static-max-age`

`def test_default_static_max_age(app):` · [tests/test_blueprints.py:L223-L224][f1]

test_default_static_max_age subclasses flask.Blueprint overriding get_send_file_max_age to return 100, registers it with a static_folder, and asserts that blueprint.send_static_file('index.html') carries Cache-Control max-age 100 even after the app config SEND_FILE_MAX_AGE_DEFAULT is changed to a different value (3600, or 7200 if it already equals 3600) — the blueprint override wins.

The config is restored in a finally block because the fixture app is shared.

contract: [test_templates_and_static](r2-blueprint-tests.md#u-c2739970c806)

<a id="u-08a9d9d7bbc4"></a>
### `test-blueprints-template-filters`

`def test_template_filter(app):` · [tests/test_blueprints.py:L362-L365][f1]

These tests register a reversing string filter on a blueprint via either the decorator @bp.app_template_filter() or bp.add_app_template_filter(fn), optionally with an explicit name (e.g. 'strrev', or 'super_reverse' for a function named my_reverse).

After app.register_blueprint, the filter appears in app.jinja_env.filters under the explicit name when given, else the function name, and behaves as s[::-1]. The *_with_template and after_route variants additionally render template_filter.html through a client request ('abcd' -> 'dcba'), showing the filter is effective whether the blueprint is registered before or after the route is defined, including via the add_app_template_filter call form.

<a id="u-42b15dc6b81e"></a>
### `test-blueprints-template-tests`

`def test_template_test(app):` · [tests/test_blueprints.py:L498-L501][f1]

These tests register a template test (isinstance(value, bool)) on a blueprint via @bp.app_template_test() or bp.add_app_template_test(fn), optionally with an explicit name 'boolean'.

After registration the test appears in app.jinja_env.tests under the given or function name and returns True for False. The *_with_template and after_route variants render template_test.html with value=False through a client request and assert 'Success!' in the body, showing the test is active whether registered before or after the route, and in both decorator and explicit-call forms.

<a id="u-80e72057fd8c"></a>
### `test-blueprints-url-defaults`

`def test_blueprint_url_defaults(app, client):` · [tests/test_blueprints.py:L131-L134][f1]

These tests cover url_defaults and route defaults.

test_blueprint_url_defaults registers one blueprint twice (name 'test2') with blueprint-level url_defaults {'bar': 23} and {'bar': 19}; combined with the route-level defaults {'baz': 42}, /1/foo renders '23/42' and /2/foo '19/42', and /1/bar, /2/bar use the blueprint defaults. test_empty_url_defaults registers one view twice — a '/' route with defaults {'page': 1} and a '/page/<int:page>' route — so '/' renders '1' and '/page/2' renders '2'.

**Uncertainties.**

- Whether registering the same blueprint object twice copies or shares state is not visible here

<a id="u-01cb4f929d78"></a>
### `test-blueprints-url-processors`

`def test_blueprint_url_processors(app, client):` · [tests/test_blueprints.py:L151-L154][f1]

These tests verify URL value processors.

In test_blueprint_url_processors a blueprint with url_prefix '/<lang_code>' installs a bp.url_defaults handler that injects g.lang_code via values.setdefault and a bp.url_value_preprocessor that pops lang_code from incoming values onto flask.g; index/about round-trip url_for('.about')/url_for('.index') producing '/de/about' and '/de/'. test_app_url_processors uses bp.app_url_defaults and bp.app_url_value_preprocessor with app-level routes, showing those variants apply to all app URLs. Graph evidence for setdefault/pop is ambiguous across three candidate implementations, so the concrete g implementation is not asserted.

uses: [_AppCtxGlobals](r2-app-context-and-globals.md#u-0fcc88751f58)

**Uncertainties.**

- Which setdefault/pop implementation (e.g. _AppCtxGlobals) is actually used cannot be proven from this source

<a id="u-9aa843f29bc7"></a>
### `test_app_request_processing`

`def test_app_request_processing(app, client):` · [tests/test_blueprints.py:L727-L731][f1]

Verifies app-wide lifecycle callbacks registered on a blueprint via before_app_request, after_app_request, and teardown_app_request.

They fire for an app-level route defined outside the blueprint: before any request evts is empty; each request returns b'request|after' and appends ['before', 'after', 'teardown']; a second request doubles the list, showing the callbacks run on every request, not once.

<a id="u-f7c1bc7e476c"></a>
### `test_blueprint_renaming`

`def test_blueprint_renaming(app, client) -> None:` · [tests/test_blueprints.py:L1017-L1021][f1]

Verifies that registering the same blueprint under multiple names gives distinct endpoint prefixes.

bp is registered at /a as 'bp' and at /b as 'alt'; bp2 is nested into bp at /a with name 'sub'. /a/ yields endpoint 'bp.index', /b/ 'alt.index', /a/a/ 'bp.sub.index2', /b/a/ 'alt.sub.index2'. The 403 errorhandler registered on bp works under both registrations: /a/error and /b/error both return 'Error'.

contract: [test_unique_blueprint_names](r2-blueprint-tests.md#u-9770bade23bb)

<a id="u-a2ce5e70fa82"></a>
### `tests/test_blueprints.py:test_request_processing`

`def test_request_processing(app, client):` · [tests/test_blueprints.py:L696-L700][f1]

Verifies blueprint-scoped request lifecycle callbacks.

before_request appends 'before', after_request appends '|after' to the response body and 'after' to evts, teardown_request appends 'teardown'. evts is empty before any request; one request to /bp returns b'request|after' and produces the event order ['before', 'after', 'teardown'], i.e. teardown runs after the response is produced.

<a id="u-533ae5559c37"></a>
### `test_self_registration`

`def test_self_registration(app, client) -> None:` · [tests/test_blueprints.py:L1011-L1014][f1]

Asserts that bp.register_blueprint(bp) — registering a blueprint into itself — raises ValueError.

<a id="u-7d4af9c5c1cb"></a>
### `test_template_global`

`def test_template_global(app):` · [tests/test_blueprints.py:L675-L678][f1]

Registers get_answer on a blueprint via @bp.app_template_global() and verifies it is absent from app.jinja_env.globals before registration and present (identical object, returning 42) after.

Within an app context, render_template_string('{{ get_answer() }}') yields '42', showing the app-scoped template global becomes usable in rendering once the blueprint is registered.

imports: [test_blueprints.py module code (L1–L7)][f1]

<a id="u-c2739970c806"></a>
### `test_templates_and_static`

`def test_templates_and_static(test_apps):` · [tests/test_blueprints.py:L176-L220][f1]

Verifies blueprint template and static file resolution against the blueprintapp fixture app.

Requests return frontend/admin template bodies, admin static files including one from a nested static folder, and url_for('admin.static', ...) builds '/admin/static/test.txt'. It then adjusts SEND_FILE_MAX_AGE_DEFAULT (picking 7200 if the current value would equal the probe 3600) and asserts the Cache-Control max-age matches, restoring the original value in a finally block because other tests reuse this app. A missing template raises TemplateNotFound whose .name is checked, and a separate app's request context still renders a template found through a blueprint's nested template path.

**Notes.**

- side_effect: SEND_FILE_MAX_AGE_DEFAULT is saved and restored in try/finally so the shared fixture app is left unchanged
- condition: expected_max_age flips from 3600 to 7200 when the current config already equals 3600, to ensure the asserted value actually changed

imports: [test_blueprints.py module code (L1–L7)][f1]

**Uncertainties.**

- Template lookup precedence between blueprint and app folders is observed only through the fixture app's layout, which is not supplied

<a id="u-3bd593eb91fb"></a>
### `test_templates_list`

`def test_templates_list(test_apps):` · [tests/test_blueprints.py:L247-L251][f1]

Asserts that app.jinja_env.list_templates() on the blueprintapp fixture returns exactly the sorted union of blueprint templates: ['admin/index.html', 'frontend/index.html'], showing blueprint template folders are merged into the app's Jinja loader listing.

imports: [test_blueprints.py module code (L1–L7)][f1]

**Uncertainties.**

- The fixture app's blueprint registration is not in this source

<a id="u-9770bade23bb"></a>
### `test_unique_blueprint_names`

`def test_unique_blueprint_names(app, client) -> None:` · [tests/test_blueprints.py:L994-L1008][f1]

Verifies registration-name collision rules: registering the same blueprint twice under its original name raises ValueError; the same blueprint re-registered with name='again' succeeds; a different blueprint with the same original name raises ValueError; and a different blueprint under name='alt' succeeds.

Registration names, not blueprint identity alone, must be unique per app.

**Uncertainties.**

- The precise condition raising ValueError (name already registered vs blueprint already registered) is observed only through these four cases

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_blueprints.py
