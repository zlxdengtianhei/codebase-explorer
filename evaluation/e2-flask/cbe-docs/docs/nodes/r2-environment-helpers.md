# Environment and Path Helpers

**Capability.** get_debug_flag and get_load_dotenv read FLASK_DEBUG / FLASK_SKIP_DOTENV; get_root_path locates a module's directory; _split_blueprint_path expands dotted blueprint names to their ancestor chain.

Infrastructure used by the CLI (debug and dotenv flags), app/bp construction (root paths), and Request.blueprints (blueprint ancestry).

**Depended on by.**

- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · model-inferred · 0 edge(s)
- [Concrete WSGI Application](r1-concrete-app.md) · graph-only · 2 edge(s)
- [App Discovery and Loading](r2-cli-app-discovery.md) · graph-only · 2 edge(s)
- [Sans-I/O Application Core](r1-core-app-model.md) · graph-only · 1 edge(s)
- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 1 edge(s)
- [URL Building, Redirects, and Resources](r1-url-building-resources.md) · graph-only · 1 edge(s)
- [Run, Shell, and Routes Commands](r2-cli-server-commands.md) · graph-only · 1 edge(s)
- [Request and Response Wrappers](r2-request-response-objects.md) · graph-only · 1 edge(s)

Parent: [Shared Helpers](r2-helpers-utilities.md)

## Units (4)

<a id="u-88884dd6c1eb"></a>
### `get_debug_flag`

`def get_debug_flag() -> bool:` · [src/flask/helpers.py:L27-L32][f1]

Reads FLASK_DEBUG from the environment and returns whether debug mode should be on.

Any unset/empty value, '0', 'false', or 'no' (case-insensitive) yields False; any other non-empty value yields True. Default is False.

**Notes.**

- condition: Empty string counts as unset, returning False.

<a id="u-1ebc0586f976"></a>
### `get_load_dotenv`

`def get_load_dotenv(default: bool = True) -> bool:` · [src/flask/helpers.py:L35-L47][f1]

Reports whether dotenv files should be loaded, based on FLASK_SKIP_DOTENV.

If the variable is unset or empty, returns the default parameter (True). Otherwise returns True only when the value is '0', 'false', or 'no' case-insensitively, meaning dotenv loading stays enabled when the skip variable is explicitly falsy.

**Notes.**

- contract: Callers may pass default=False to opt out when the env var is absent.

<a id="u-da4504f7f768"></a>
### `get_root_path`

`def get_root_path(import_name: str) -> str:` · [src/flask/helpers.py:L570-L624][f1]

Finds the filesystem directory containing a module or package, returning the current working directory when it cannot be determined.

Order of attempts: if the module is already imported with a non-None __file__, return its dirname; otherwise find_spec — an ImportError/ValueError (including spec None) sets loader to None; a None loader (unloaded main module, interactive session) returns os.getcwd(). With a loader, use loader.get_filename if available; otherwise import the module and read __file__, raising RuntimeError when still absent (import hooks without filename info or namespace packages). Finally returns dirname(abspath(filepath)).

**Uncertainties.**

- Whether find_spec can raise other exception types is not handled; only ImportError/ValueError are caught

<a id="u-03dadcbb1883"></a>
### `_split_blueprint_path`

`def _split_blueprint_path(name: str) -> list[str]:` · [src/flask/helpers.py:L627-L634][f1]

Returns the name and all its dotted parent names, e.g. 'a.b.c' -> ['a.b.c', 'a.b', 'a'].

Recurses on name.rpartition('.')[0] when a dot is present; decorated with @cache so results are memoized process-wide, meaning the returned list is shared between callers.

**Notes.**

- side_effect: functools.cache retains every result for process lifetime; mutating the returned list affects the cached value.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/helpers.py
