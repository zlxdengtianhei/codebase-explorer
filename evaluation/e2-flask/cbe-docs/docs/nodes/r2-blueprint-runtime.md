# Concrete Blueprint Runtime

**Capability.** The flask.Blueprint class extending the sansio blueprint with runtime behavior: static file serving with per-config cache max-age, resource opening under root_path, and a Click command group.

Read this for the runtime-facing blueprint API. send_static_file delegates to helpers.send_from_directory and resolves max-age from SEND_FILE_MAX_AGE_DEFAULT, allowing subclass overrides.

**Depends on.**

- [File Serving Helpers](r2-file-serving-helpers.md) · graph-confirmed · 1 edge(s) · Blueprint.send_static_file delegates static file delivery to send_from_directory.
- [Blueprint Deferred Setup](r2-sansio-blueprint-core.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Blueprint Test Suite](r2-blueprint-tests.md) · model-inferred · 0 edge(s)

Parent: [Blueprint System](r2-blueprint-system.md)

## Units (5)

<a id="u-340cf74dd862"></a>
### `Blueprint`

`class Blueprint(SansioBlueprint):` · [src/flask/blueprints.py:L18-L19][f1]

Concrete blueprint class extending the sansio blueprint with runtime helpers for static files, resources, and CLI.

Adds an AppGroup CLI named after the blueprint, and duplicates the app's static-file serving logic so blueprints can serve their own static folders and open resource files relative to their root path.

group: [Blueprint.__init__](r2-blueprint-runtime.md#u-2111fdf38502), [Blueprint.get_send_file_max_age](r2-blueprint-runtime.md#u-b3f294891469), [Blueprint.send_static_file](r2-blueprint-runtime.md#u-9d50961e7564), [Blueprint.open_resource](r2-blueprint-runtime.md#u-79aeaf78f841)

**Uncertainties.**

- Behavior of SansioBlueprint.__init__ setup (registration, routing) lives outside this file and is not verified here

<a id="u-2111fdf38502"></a>
### `Blueprint.__init__`

`def __init__( self, name: str, import_name: str, static_folder: str | os.PathLike[str…` · [src/flask/blueprints.py:L19-L53][f1]

Initializes a blueprint by delegating all ten constructor parameters positionally to the sansio superclass, then attaches a Click command group.

After super().__init__ completes, it assigns self.cli = AppGroup() and sets the group's name to self.name, so blueprint CLI commands can be exposed under the blueprint's name when registered with an app. Raises nothing itself; any validation comes from the superclass.

**Uncertainties.**

- Whether SansioBlueprint accepts cli_group=_sentinel specially is defined in sansio code not supplied here

<a id="u-b3f294891469"></a>
### `Blueprint.get_send_file_max_age`

`def get_send_file_max_age(self, filename: str | None) -> int | None:` · [src/flask/blueprints.py:L55-L80][f1]

Resolves the cache max-age used when serving a file, based on the current app's SEND_FILE_MAX_AGE_DEFAULT config.

Returns None when the config is None (browser uses conditional requests), converts a timedelta to int total seconds, and returns any other value unchanged. The filename parameter is accepted but unused in the body shown.

**Uncertainties.**

- filename is ignored in the visible body; whether any branch uses it cannot be confirmed

<a id="u-79aeaf78f841"></a>
### `Blueprint.open_resource`

`def open_resource( self, resource: str, mode: str = "rb", encoding: str | None = "utf…` · [src/flask/blueprints.py:L104-L128][f1]

Opens a resource file located under the blueprint's root_path.

Raises ValueError for any mode other than 'r', 'rt', or 'rb' (reading only); joins root_path with the resource path, then opens in binary mode without encoding, or text mode with the given encoding (default utf-8). Returns the open file object; OS errors from open propagate.

**Notes.**

- failure: ValueError raised before any file access for write-capable or unknown modes.

**Uncertainties.**

- No path-existence or traversal check beyond os.path.join; invalid resources surface as filesystem errors

<a id="u-9d50961e7564"></a>
### `Blueprint.send_static_file`

`def send_static_file(self, filename: str) -> Response:` · [src/flask/blueprints.py:L82-L102][f1]

View function serving a file from the blueprint's static folder.

Raises RuntimeError if has_static_folder is false; otherwise computes max_age via this blueprint's get_send_file_max_age (so blueprint config applies even though send_file normally only queries the app) and delegates to send_from_directory with the static folder cast to str.

calls: [Blueprint.get_send_file_max_age](r2-blueprint-runtime.md#u-b3f294891469), [send_from_directory](r2-file-serving-helpers.md#u-b61c28e0e520)

**Uncertainties.**

- has_static_folder is defined in sansio/scaffold code not supplied

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/blueprints.py
