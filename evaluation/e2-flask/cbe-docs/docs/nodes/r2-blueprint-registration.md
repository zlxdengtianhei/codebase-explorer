# Blueprint Registration

**Capability.** Applies deferred functions to an application: Blueprint.register walks state, BlueprintSetupState namespaces URL rules under the blueprint name, and _merge_blueprint_funcs copies handler/template lists into app dicts with renamed keys.

Use this to trace exactly what happens when register_blueprint runs, including endpoint renaming ('name.key'), name-None app-scope keys, and how nested blueprints recurse through register.

**Depends on.**

- [Request and Response Wrappers](r2-request-response-objects.md) · model-inferred · 0 edge(s)
- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) · graph-confirmed · 1 edge(s) · register consumes the deferred setup functions recorded by the sansio blueprint core.
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Blueprint Test Suite](r2-blueprint-tests.md) · model-inferred · 0 edge(s)
- [Sans-I/O Application Core](r1-core-app-model.md) · graph-only · 1 edge(s)
- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) · graph-only · 1 edge(s)
- [Flask Framework](r2-flask-framework.md) · within containment · 1 edge(s)

Parent: [Blueprint System](r2-blueprint-system.md)

## Units (5)

<a id="u-b4e76012bbf2"></a>
### `BlueprintSetupState`

`class BlueprintSetupState:` · [src/flask/sansio/blueprints.py:L34-L41][f1]

Holds the temporary registration context created by Blueprint.make_setup_state and passed to every deferred setup callback when a blueprint registers on an app.

Effective values prefer register-time options over blueprint defaults: subdomain and url_prefix come from options with fallback to the blueprint attributes; name defaults to the blueprint name and name_prefix to ''. Instances are read-heavy holders; registration mechanics live in add_url_rule.

group: [BlueprintSetupState](r2-blueprint-registration.md#u-b4e76012bbf2), [BlueprintSetupState.add_url_rule](r2-blueprint-registration.md#u-14b96816dcf8)

<a id="u-14b96816dcf8"></a>
### `BlueprintSetupState.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/blueprints.py:L87-L116][f1]

Registers one URL rule on the target application with blueprint namespacing.

If the state has a url_prefix, the rule is joined as prefix.rstrip('/') + '/' + rule.lstrip('/'); an empty rule becomes just the prefix. subdomain is injected into options only if the caller did not supply one. When endpoint is None it is derived from the view function via _endpoint_from_view_func. An options-level 'defaults' is merged over the state's url_defaults and popped from options. The final endpoint is 'name_prefix.name.endpoint' with leading dots stripped, then delegated to app.add_url_rule with defaults and remaining options.

**Notes.**

- contract: A None endpoint with a None view_func makes _endpoint_from_view_func derive the endpoint from None; the failure mode lives in that helper.

calls: [_endpoint_from_view_func](r1-scaffold-shared-base.md#u-5eef70528339)

**Uncertainties.**

- unlike Blueprint.add_url_rule, no dot validation of endpoint or view_func name occurs here; malformed names surface only via app.add_url_rule behavior outside this file

<a id="u-e0d107e183f6"></a>
### `Blueprint.register`

`def register(self, app: App, options: dict[str, t.Any]) -> None:` · [src/flask/sansio/blueprints.py:L273-L377][f1]

Registers this blueprint's views and callbacks on an application, invoked by App.register_blueprint.

Computes the effective name as 'name_prefix.name' with leading dots stripped; if that name is already in app.blueprints, raises ValueError distinguishing whether the existing entry is this same blueprint or a different one, and suggesting 'name='. Otherwise records first_bp_registration (no prior instance of self on the app) and first_name_registration, stores self in app.blueprints under the name, sets _got_registered_once, and builds a setup state. If the blueprint has a static folder, a static route '<static_url_path>/<path:filename>' pointing at send_static_file with endpoint 'static' is added through the state. When it is the first instance or first use of the name, _merge_blueprint_funcs copies handlers into the app. Every deferred function then runs with the state. CLI commands: if cli_resolved_group (options['cli_group'] or self.cli_group) is None the commands merge flat into app.cli.commands; if it is _sentinel the group is added under the full dotted name; otherwise the group is added under the given group name. Finally, each nested blueprint is registered recursively: its options are copied, subdomain and url_prefix are combined — both set: child value joined onto parent (prefix rstrip+'/' + child lstrip, subdomain as 'child.state'); only child set: child value; only state set: state value — and 'name_prefix' is set to this blueprint's full name before recursing.

calls: [BlueprintSetupState.add_url_rule](r2-blueprint-registration.md#u-14b96816dcf8), [Blueprint.make_setup_state](r2-sansio-blueprint-core.md#u-cdd8d4a4352d), [Blueprint._merge_blueprint_funcs](r2-blueprint-registration.md#u-50f99a1d3f51); contract: [Blueprint.register_blueprint](r2-sansio-blueprint-core.md#u-f6af7e7aaa66)

**Uncertainties.**

- the docstring cites versioned behavior; only the current code path is verifiable here
- re-registering the same blueprint object under a different name succeeds and re-runs deferred functions with first_registration=False for that instance; downstream idempotency depends on record_once wrappers

<a id="u-50f99a1d3f51"></a>
### `Blueprint._merge_blueprint_funcs`

`def _merge_blueprint_funcs(self, app: App, name: str) -> None:` · [src/flask/sansio/blueprints.py:L379-L380][f1]

Merges blueprint-level data into the application under the registration name.

Error handlers are copied into app.error_handler_spec keyed by 'name' or 'name.key', rebuilt as a defaultdict of dicts keyed by status code then exception class. View functions are copied by endpoint directly into app.view_functions. The helper extend copies hook lists (before/after request, teardown, url defaults, url value preprocessors, template context processors), remapping None keys to the blueprint name and dotted keys to 'name.key', appending onto the app's lists.

**Uncertainties.**

- called only when first_bp_registration or first_name_registration (register), so a repeat registration under a new name re-merges; whether that duplicates entries in app lists is not guarded here beyond extend appending

<a id="u-06ffb503b27c"></a>
### `extend`

`def extend( bp_dict: dict[ft.AppOrBlueprintKey, list[t.Any]], parent_dict: dict[ft.Ap…` · [src/flask/sansio/blueprints.py:L380-L386][f1]

Copies each key's list from a blueprint dict into the parent app dict, renaming None to the blueprint name and other keys to 'name.key', appending values.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/blueprints.py
