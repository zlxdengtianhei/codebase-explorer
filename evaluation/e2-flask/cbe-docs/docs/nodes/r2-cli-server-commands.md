# Run, Shell, and Routes Commands

**Capability.** Implements the concrete development commands: the dev server with cert/key validation and startup banner, the app-context shell, and the route table listing.

Consult this for options and behavior of `flask run`, `flask shell`, and `flask routes`, including the Click parameter types (CertParamType, SeparatedPathType) that support them.

**Depends on.**

- [App Discovery and Loading](r2-cli-app-discovery.md) · graph-confirmed · 1 edge(s)
- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · graph-confirmed · 2 edge(s) · The shell and routes commands wrap their execution in with_appcontext.
- [Environment and Path Helpers](r2-environment-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [CLI Test Suite](r2-cli-tests.md) · model-inferred · 0 edge(s)
- [Concrete WSGI Application](r1-concrete-app.md) · graph-only · 1 edge(s)

Parent: [Command-Line Interface](r2-cli-system.md)

## Units (8)

<a id="u-507bfc125783"></a>
### `run_command`

`def run_command( info: ScriptInfo, host: str, port: int, reload: bool, debugger: bool…` · [src/flask/cli.py:L882-L963][f1]

Implements 'flask run', the development-server command decorated with host, port, cert, key, reload, debugger, threads, extra-files, and exclude-patterns options.

It loads the app via ScriptInfo: on failure under the reloader it prints the traceback immediately but defers the error by returning a WSGI app that re-raises it on first request; otherwise it re-raises so the command fails now. debug comes from get_debug_flag; reload and debugger default to that debug value when their flags were omitted. It prints the server banner and calls werkzeug's run_simple with the resolved reloader, debugger, threading, SSL context, extra files, and exclude patterns. A module-level statement inserts the shared --debug option as the command's first parameter.

calls: [show_server_banner](r2-cli-server-commands.md#u-b8abb08fd76f), [get_debug_flag](r2-environment-helpers.md#u-88884dd6c1eb); uses: [CertParamType](r2-cli-server-commands.md#u-24f31c731d02), [_validate_key](r2-cli-server-commands.md#u-d4711d5746d9)

**Uncertainties.**

- The reloader-deferred-error app raises on every request; whether run_simple inspects the app before calling it is outside this source.

<a id="u-24f31c731d02"></a>
### `CertParamType`

`class CertParamType(click.ParamType):` · [src/flask/cli.py:L780-L788][f1]

Click param type for the --cert option, accepting an existing file path, 'adhoc', or an import string for an ssl.SSLContext.

__init__ builds the underlying click.Path(exists=True, resolve_path=True). convert first imports ssl, raising BadParameter if Python lacks SSL support. It tries the path validation; on BadParameter it lowercases the value as a string: 'adhoc' returns the string after verifying the cryptography package is importable (otherwise BadParameter); any other value is imported with import_string(silent=True) and returned if it is an ssl.SSLContext; otherwise the original BadParameter from the path check is re-raised.

<a id="u-d4711d5746d9"></a>
### `_validate_key`

`def _validate_key(ctx: click.Context, param: click.Parameter, value: t.Any) -> t.Any:` · [src/flask/cli.py:L828-L864][f1]

Cross-validates the --key option against the already-parsed --cert parameter.

It determines whether cert is 'adhoc' or an ssl.SSLContext (is_context False when ssl is unavailable). If a key value was given: 'adhoc' cert raises BadParameter (key unused), an SSLContext cert raises BadParameter (key unused), and a missing cert raises BadParameter ('--cert' must be specified); otherwise cert is replaced with a (cert, key) tuple in ctx.params. If no key was given, a cert that is neither adhoc nor an SSLContext raises BadParameter ('Required when using --cert'). The key value is returned.

<a id="u-b8abb08fd76f"></a>
### `show_server_banner`

`def show_server_banner(debug: bool, app_import_path: str | None) -> None:` · [src/flask/cli.py:L766-L777][f1]

Prints startup messages for the development server.

It returns immediately when running under the reloader; otherwise it echoes the served app's import path when known and a 'Debug mode: on/off' line when debug is not None.

**Uncertainties.**

- The debug-is-None branch (no message) is implied by the truthiness check, not an explicit None comparison.

<a id="u-21939f98a070"></a>
### `routes_command`

`def routes_command(sort: str, all_methods: bool) -> None:` · [src/flask/cli.py:L1048-L1107][f1]

Implements 'flask routes', wrapped in with_appcontext.

It lists URL rules from the current app: with no rules it prints a message and returns. Unless --all-methods is given, HEAD and OPTIONS are excluded from each rule's method list. When any rule has a host (host matching) or subdomain, a Host/Subdomain column is added. Rows are sorted by the --sort key (endpoint, methods, domain, rule, or match); an out-of-range sort value falls through silently via ValueError. Output is a fixed-width table built from computed column widths, with header and dashed-separator rows.

uses: [with_appcontext](r2-cli-command-group.md#u-5dadcd365659)

**Uncertainties.**

- 'match' is accepted by --sort but sorts via the same index list; its actual match order depends on url_map internals not shown here.

<a id="u-43159ceb5ced"></a>
### `shell_command`

`def shell_command() -> None:` · [src/flask/cli.py:L999-L1045][f1]

Implements 'flask shell', wrapped in with_appcontext so the current app is loaded.

It builds a banner showing the Python version, app import name, and instance path. The shell namespace starts empty; if PYTHONSTARTUP names an existing file it is exec'd into that namespace, then app.make_shell_context() results are merged. If a sys.__interactivehook__ exists it is invoked; when the readline/rlcompleter imports succeed, the completer is pointed at the shell context instead of __main__ so completion resolves Flask names. Finally code.interact runs with the banner and namespace.

uses: [with_appcontext](r2-cli-command-group.md#u-5dadcd365659)

<a id="u-137becebe47f"></a>
### `SeparatedPathType`

`class SeparatedPathType(click.Path):` · [src/flask/cli.py:L867-L873][f1]

click.Path subclass accepting multiple values separated by the OS path separator.

Its convert splits the raw value with split_envvar_value and returns a list where each item is validated by the parent click.Path.convert, so each component must individually satisfy the path constraints.

<a id="u-893b72fd2f0c"></a>
### `_path_is_ancestor`

`def _path_is_ancestor(path: str, other: str) -> bool:` · [src/flask/cli.py:L691-L695][f1]

Returns True if path is an ancestor directory of other: it takes the remainder of other after path's length, strips leading separators, joins it back onto path, and compares to the original other.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/cli.py
