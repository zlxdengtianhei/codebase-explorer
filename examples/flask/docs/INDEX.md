# flask: code map

This repository is the Flask WSGI micro-framework. A sansio layer holds the I/O-free Scaffold, Blueprint and App base classes that handle route, handler and callback registration, and the concrete Flask app builds on them. The runtime modules cover the per-request pipeline (WSGI entry, dispatch, response finalization, error handling), app and request contexts, and the test client and CLI runner. The command line and public helpers, templating, views and wrappers, sessions, tagged JSON, JSON providers and configuration loading each have their own module.

## Modules

- [**Sansio App and Scaffold Foundations**](nodes/sansio-app-and-scaffold-foundations.md) — Provides the framework-agnostic foundations that the concrete Flask app and blueprints build on: shared scaffold registration, blueprint recording, app base setup and logging. (74 units)
  - [**Scaffold and Blueprint Registration**](nodes/scaffold-and-blueprint-registration.md) — Defines how routes, handlers and callbacks are declared and deferred, through the shared Scaffold base and the sansio Blueprint that builds on it. (43 units)
  - [**Sansio App Base and Logging**](nodes/sansio-app-base-and-logging.md) — Defines the framework-agnostic application base class and the logger setup it uses, covering app construction, configuration and Jinja environment preparation. (31 units)
- [**Runtime App, Contexts and Testing**](nodes/runtime-app-contexts-and-testing.md) — Covers the running application: the concrete Flask app and request lifecycle, the contexts that bind per-request state, and the tools for testing apps. (64 units)
  - [**Flask App Request Lifecycle**](nodes/flask-app-request-lifecycle.md) — Implements the concrete Flask application and its request lifecycle: WSGI entry, dispatch, response finalization and exception handling, grouped as the app's per-request pipeline. (34 units)
  - [**Test Client and CLI Runner**](nodes/test-client-and-cli-runner.md) — Offers testing tools: an environment builder with app defaults, a context-aware test client with session editing, and an app-aware CLI runner. (15 units)
  - [**App and Request Context Management**](nodes/app-and-request-context-management.md) — Defines application and request contexts, the g namespace and context helpers that bind per-app and per-request state, URL matching and session opening. (15 units)
- [**Command Line and Public Helpers**](nodes/command-line-and-public-helpers.md) — Provides the user-facing command line interface together with public helper functions, the WSGI-aware Blueprint and the app run method that developers call directly. (58 units)
  - [**Flask CLI Implementation**](nodes/flask-cli-implementation.md) — Implements the flask command line: parameter types, app loading and import discovery, the command groups, built-in commands and the development server command. (38 units)
  - [**Helpers, Flask Blueprint and Run**](nodes/helpers-flask-blueprint-and-run.md) — Gathers public helper functions (url_for, redirect, flash, send_file, abort, debug flags), the WSGI-aware Blueprint, and the app's run method. (20 units)
- [**Templates, Views and Wrappers**](nodes/templates-views-and-wrappers.md) — Groups the view-layer pieces: Jinja template rendering and loading with class-based views, request and response wrappers, signals and debugging aids. (39 units)
  - [**Views, Wrappers, Signals and Debug Aids**](nodes/views-wrappers-signals-and-debug-aids.md) — Provides class-based views, request and response wrapper classes, signals, debug helper errors and template loading diagnostics, plus the python -m entry point. (21 units)
  - [**Template Rendering and Loading**](nodes/template-rendering-and-loading.md) — Handles Jinja integration: the app-bound environment, a loader spanning app and blueprints, and render and stream functions with signals and context processors. (18 units)
- [**Tagged JSON Serialization**](nodes/tagged-json-serialization.md) — Implements TaggedJSONSerializer and its tag classes, which encode non-JSON types such as bytes, datetime, tuple and UUID into JSON-compatible structures and back. (16 units)
- [**JSON Providers and Helpers**](nodes/json-providers-and-helpers.md) — Defines the pluggable JSON provider interface, its default implementation, and module-level dumps, loads and jsonify functions that use the current app's provider. (14 units)
- [**Session Interface and Cookies**](nodes/session-interface-and-cookies.md) — Implements sessions: session classes, the abstract session interface and the default signed-cookie backend with cookie settings, expiry and save decisions. (14 units)
- [**Configuration Loading**](nodes/configuration-loading.md) — Implements the Config dict and its loaders from Python files, objects, mappings, data files and environment variables, plus a config-backed attribute descriptor. (14 units)

## Key flows

- **Route registration**: HTTP-method shortcuts and the route decorator reach add_url_rule, with the setupmethod guard checking that setup is not yet finished. — `scaffold.py-http-method-shortcuts` → `Scaffold._method_route` → `scaffold.py-route` → `Scaffold.add_url_rule` → `scaffold.py-setupmethod` → `Scaffold._check_setup_finished`
- **Blueprint deferred setup**: App-wide blueprint decorators defer work through record_once and record, relying on the setupmethod guard. — `blueprints.py-app-wide-request-callbacks` → `blueprints.py-record-once` → `Blueprint.record` → `scaffold.py-setupmethod` → `Scaffold._check_setup_finished`
- **Test client request**: FlaskClient.open builds the request from builder arguments using an EnvironBuilder and a copied environ. — `FlaskClient.open` → `FlaskClient._request_from_builder_args` → `EnvironBuilder.__init__` → (model-inferred) → `FlaskClient._copy_environ`
- **Running the dev server**: Flask.run consults the debug and dotenv helpers, loads dotenv files and shows the server banner. — `Flask.run` → `get_load_dotenv` → (model-inferred) → `load_dotenv` → (model-inferred) → `get_debug_flag` → (model-inferred) → `show_server_banner`
- **CLI app loading**: The run command loads the app through ScriptInfo, which prepares the import and checks the debug flag. — `cli.py-run-command` → `ScriptInfo.load_app` → `prepare_import` → (model-inferred) → `get_debug_flag`
- **URL building**: Flask.url_for injects URL defaults and uses blueprint path helpers while building a URL. — `Flask.url_for` → `App.inject_url_defaults` → `_split_blueprint_path`
- **App instance path discovery**: App construction finds the instance path by locating the package and its path. — `App.__init__` → `App.auto_find_instance_path` → `find_package` → `_find_package_path`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
