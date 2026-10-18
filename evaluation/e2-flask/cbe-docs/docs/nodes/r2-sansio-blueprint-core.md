# Blueprint Deferred Setup

**Capability.** Represents a blueprint as a list of deferred setup functions: record/record_once append callbacks, _check_setup_finished guards post-registration mutation, and register_blueprint stages nested blueprints.

Read this to see how blueprint decorators work without an application: nothing touches an app until registration. record_once ensures app-scope callbacks run only on first registration.

**Depends on.**

- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 3 edge(s)
- [Blueprint Registration](r2-blueprint-registration.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Blueprint Registration](r2-blueprint-registration.md) · graph-confirmed · 1 edge(s) · register consumes the deferred setup functions recorded by the sansio blueprint core.
- [Concrete Blueprint Runtime](r2-blueprint-runtime.md) · model-inferred · 0 edge(s)
- [App-Scope Blueprint Hooks](r2-blueprint-app-integrations.md) · graph-only · 10 edge(s)

Parent: [Blueprint System](r2-blueprint-system.md)

## Units (9)

<a id="u-4d2993c6ddda"></a>
### `blueprints-py-module-header`

`module_region` · [src/flask/sansio/blueprints.py:L1-L33][f1]

Module header of the sansio blueprint module: imports and type aliases forming the deferred-setup vocabulary.

DeferredSetupFunction names the callback signature taking a BlueprintSetupState; the T_* TypeVars bind the app-level hook decorators to their callable protocols. TYPE_CHECKING imports App for annotations only.

<a id="u-d7d5b4b4bcc2"></a>
### `src/flask/sansio/blueprints.py:Blueprint`

`class Blueprint(Scaffold):` · [src/flask/sansio/blueprints.py:L119-L174][f1]

Represents a blueprint: routes, error handlers, template hooks, and CLI commands defined without an application, recorded as deferred functions and applied at registration.

Subclasses Scaffold for root-path resolution, static-folder support, and the @setupmethod guard that forbids setup calls after registration begins. Class attribute _got_registered_once flips on first register() and gates _check_setup_finished. Decorators such as app_template_filter and the app_* request hooks all funnel through record_once so their side effects run only on the first registration; nested blueprints are staged in _blueprints and registered recursively with dotted names and merged prefixes/subdomains.

uses: [setupmethod](r1-scaffold-shared-base.md#u-81ccd06c4290)

**Uncertainties.**

- inherited Scaffold behavior (root_path detection, static file sending, cli construction) is defined in src/flask/sansio/scaffold.py and only invoked here

<a id="u-6140c4847d46"></a>
### `src/flask/sansio/blueprints.py:Blueprint.__init__`

`def __init__( self, name: str, import_name: str, static_folder: str | os.PathLike[str…` · [src/flask/sansio/blueprints.py:L174-L211][f1]

Builds a blueprint.

Delegates import_name, static_folder, static_url_path, template_folder, and root_path to Scaffold.__init__ before validating the name: empty or containing a dot raises ValueError, since dots are the endpoint namespace separator. Stores url_prefix and subdomain, initializes deferred_functions, copies a None url_defaults to {}, keeps cli_group (default the _sentinel marker meaning 'derive from name'), and starts an empty _blueprints list for nested registrations.

**Uncertainties.**

- Scaffold.__init__ failure modes (e.g. import_name resolution) are outside this file

<a id="u-6560000f6f91"></a>
### `Blueprint._check_setup_finished`

`def _check_setup_finished(self, f_name: str) -> None:` · [src/flask/sansio/blueprints.py:L213-L221][f1]

Guard: raises AssertionError if _got_registered_once is True, stating that the named setup method can no longer be called consistently on this blueprint and setup must finish before registering.

No-op while the blueprint has never been registered; f_name only shapes the message.

**Uncertainties.**

- whether each @setupmethod-decorated method calls this check depends on setupmethod's implementation in scaffold.py

<a id="u-26efb075394f"></a>
### `Blueprint.record`

`def record(self, func: DeferredSetupFunction) -> None:` · [src/flask/sansio/blueprints.py:L223-L230][f1]

Appends a deferred setup function to deferred_functions; each is invoked with a BlueprintSetupState during register().

No wrapping or dedup occurs.

<a id="u-e3ba6a576fc5"></a>
### `Blueprint.record_once`

`def record_once(self, func: DeferredSetupFunction) -> None:` · [src/flask/sansio/blueprints.py:L232-L240][f1]

Like record(), but wraps func so it runs only on the blueprint's first registration: the inner wrapper calls func(state) only when state.first_registration is truthy.

The wrapper's metadata is copied from func via functools.update_wrapper, then handed to record(), so re-registration of the blueprint skips the function. This is the mechanism app-scope hooks use to avoid duplicate registration.

calls: [Blueprint.record](r2-sansio-blueprint-core.md#u-26efb075394f)

<a id="u-425a9a1627fd"></a>
### `src/flask/sansio/blueprints.py:wrapper`

`def wrapper(state: BlueprintSetupState) -> None:` · [src/flask/sansio/blueprints.py:L240-L242][f1]

Inner wrapper of record_once: invokes the recorded func with the setup state only when state.first_registration is true; otherwise returns without effect.

<a id="u-f6af7e7aaa66"></a>
### `Blueprint.register_blueprint`

`def register_blueprint(self, blueprint: Blueprint, **options: t.Any) -> None:` · [src/flask/sansio/blueprints.py:L255-L271][f1]

Stages a nested blueprint for later registration by appending (blueprint, options) to _blueprints; options are applied at register() time and override blueprint defaults.

Raises ValueError if the argument is the blueprint itself, preventing self-nesting. Keyword 'name' can disambiguate repeated registrations.

<a id="u-cdd8d4a4352d"></a>
### `Blueprint.make_setup_state`

`def make_setup_state( self, app: App, options: dict[str, t.Any], first_registration: …` · [src/flask/sansio/blueprints.py:L246-L253][f1]

Creates the BlueprintSetupState passed to register callbacks, forwarding app, options, and first_registration.

Documented extension point: subclasses may override to supply a setup-state subclass.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/blueprints.py
