# CLI Test Suite

**Capability.** Pins app discovery and selection order, ScriptInfo caching, app-context wrapping, FlaskGroup nesting, dotenv loading, cert options, blueprint CLI grouping, and loading-error reporting.

Read alongside the cli-system source nodes to see expected behavior for each command and failure mode, including behavior when dotenv or the app itself is unavailable.

**Depends on.**

- [App Discovery and Loading](r2-cli-app-discovery.md) · model-inferred · 0 edge(s)
- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · model-inferred · 0 edge(s)
- [Run, Shell, and Routes Commands](r2-cli-server-commands.md) · model-inferred · 0 edge(s)
- [Configuration Loading](r2-configuration.md) · model-inferred · 0 edge(s)

Parent: [Command-Line Interface](r2-cli-system.md)

## Units (30)

<a id="u-b9fddcf86425"></a>
### `test_cli.py-test-app-cli-has-app-context`

`def test_app_cli_has_app_context(app, runner):` · [tests/test_cli.py:L289-L290][f1]

Verifies current_app is available inside Click parameter callbacks and matches the app loaded by FlaskGroup.

A click argument callback returns bool(current_app); the command loads the app via the context object's load_app and compares current_app._get_current_object() to it. Invoked with standalone_mode=False so the (same_app, value) tuple is exposed as result.return_value; both must be True.

<a id="u-41f48df3b3ab"></a>
### `test_cli.py-test-appgroup-app-context`

`def test_appgroup_app_context(runner):` · [tests/test_cli.py:L320-L321][f1]

AppGroup commands run with an app context at both nesting levels.

The top-level test command and a command inside a subgroup created with @cli.group() both echo current_app.name. Invocations pass obj=ScriptInfo(create_app=...); each expects exit code 0 and output 'testappgroup\n'.

<a id="u-718d9bcbe1d0"></a>
### `test_cli.py-test-cli-blueprints`

`def test_cli_blueprints(app):` · [tests/test_cli.py:L648-L655][f1]

Blueprint CLI commands register under groups determined by cli_group.

A blueprint with cli_group='customized' serves its command under that name; default nesting serves under the blueprint name ('nested'); cli_group=None merges commands into the root ('merged'); and a cli_group override at register_blueprint time ('late_registration') takes effect even when set after the command was defined. Each invocation via app.test_cli_runner yields the corresponding echoed result.

<a id="u-2ddc5b3ddb48"></a>
### `test_cli.py-test-find-best-app`

`def test_find_best_app(test_apps):` · [tests/test_cli.py:L48-L49][f1]

Feeds synthetic module-like classes to find_best_app and asserts its selection order.

Flask attributes named app, application, or myapp are each returned directly. Zero-argument static factories named create_app or make_app are called and their Flask return value used; a factory taking only keyword arguments also works. When both an attribute and a factory exist, the attribute wins (myapp over create_app). NoAppException is raised for an empty class, two competing Flask attributes (myapp1, myapp2), and a factory requiring positional arguments. A factory raising TypeError propagates TypeError unchanged rather than being wrapped.

uses: [test_cli_name](r2-cli-tests.md#u-25ddc0f13cfc)

**Uncertainties.**

- Relative precedence between create_app and make_app is not exercised, since each class has only one factory

<a id="u-f68fa28f84de"></a>
### `test_cli.py-test-flaskgroup-app-context`

`def test_flaskgroup_app_context(runner):` · [tests/test_cli.py:L348-L349][f1]

A FlaskGroup created with a create_app callable pushes the app context for its subcommands: the test command echoes current_app.name and a plain runner invocation of ['test'] outputs 'flaskgroup' with exit code 0, with no explicit ScriptInfo.

<a id="u-1ef4de858fe1"></a>
### `test_cli.py-test-flaskgroup-debug`

`def test_flaskgroup_debug(runner, set_debug_flag):` · [tests/test_cli.py:L365-L367][f1]

Parameterized on set_debug_flag with an app whose debug is set True in create_app.

With set_debug_flag True, FlaskGroup overrides the app's debug flag, so the command prints 'False'; with it False, the app's own debug=True survives and the command prints 'True'. Asserted output is f'{not set_debug_flag}\n'.

<a id="u-604b87fc9b0c"></a>
### `test_cli.py-test-flaskgroup-nested`

`def test_flaskgroup_nested(app, runner):` · [tests/test_cli.py:L385-L390][f1]

A FlaskGroup can be attached as a subcommand of an ordinary click.Group: the test adds a FlaskGroup named 'flask' to a plain Group and invokes ['flask', 'show']; the nested command echoes current_app.name, asserted to be the fixture app's name 'flask_test'.

<a id="u-b59bb8d1f081"></a>
### `test_cli.py-test-get-version`

`def test_get_version(test_apps, capsys):` · [tests/test_cli.py:L231-L232][f1]

Invokes get_version with a minimal mock Click context (resilient_parsing False, color None, no-op exit) and captures stdout.

Asserts output contains the running Python version plus installed Flask and Werkzeug versions read via importlib.metadata, each formatted 'Name version'.

<a id="u-9ff1d9476b8a"></a>
### `test_cli.py-test-help-echo-exception`

`def test_help_echo_exception():` · [tests/test_cli.py:L428-L429][f1]

A FlaskGroup whose create_app raises a plain Exception still answers --help with exit code 0; the exception text ('Exception: oh no') is echoed to stderr and 'Usage:' to stdout, showing load failures are reported without aborting help.

Same CliRunner fallback pattern for Click >= 8.2.

<a id="u-29ce9518b1e2"></a>
### `test_cli.py-test-prepare-import`

`def test_prepare_import(request, value, path, result):` · [tests/test_cli.py:L135-L171][f1]

Parameterized verification that prepare_import maps each input to the expected import name and sets sys.path[0] to the parent directory.

Cases cover bare names, .py stripping, path separators, package __init__ forms, nested packages under test_apps becoming dotted names, already-dotted names, absolute paths, and a non-Python file whose full name is returned so failure surfaces later at import. The test snapshots sys.path and restores it via a request finalizer so the mutation does not leak.

**Notes.**

- side_effect: prepare_import prepends the parent directory to sys.path; reset_path restores the snapshot after the test.

<a id="u-2511a9347b7f"></a>
### `test_cli.py-test-scriptinfo`

`def test_scriptinfo(test_apps, monkeypatch):` · [tests/test_cli.py:L247-L265][f1]

Exercises ScriptInfo.load_app resolution sources and caching: load_app returns the identical object on repeat calls for every source.

Sources covered are app_import_path as module:attribute, an absolute file path to cliapp/app.py with and without a :attribute suffix, and an explicit create_app callable. A ScriptInfo with none of these raises NoAppException. After monkeypatch.chdir, a bare ScriptInfo also discovers wsgi.py in the helloworld directory and app.py in the cliapp directory as the current working directory.

**Uncertainties.**

- The relative search order of wsgi.py versus app.py is not asserted; each is tested in an isolated directory

<a id="u-5916653d62a3"></a>
### `test_cli.py-test-with-appcontext`

`def test_with_appcontext(runner):` · [tests/test_cli.py:L307-L308][f1]

A plain Click command decorated with with_appcontext can read current_app.

The command echoes current_app.name; invoking it with obj=ScriptInfo(create_app=lambda: Flask("testapp")) yields exit code 0 and output 'testapp\n', showing the decorator pushes an app context built from the ScriptInfo object.

<a id="u-06ca81e88b9d"></a>
### `test_cli.py-testroutes`

`class TestRoutes:` · [tests/test_cli.py:L446-L447][f1]

Verifies the routes command's output via a FlaskGroup built on a fixture app with two registered rules.

Default order sorts by endpoint (aaa_post, static, yyy_get_post); -s endpoint matches default, -s methods sorts by methods, -s rule by rule, and -s match by registration order from url_map.iter_rules. --all-methods adds GET, HEAD, OPTIONS, POST to each row, absent by default. An app with no static folder and no rules prints 'No routes were registered.'; subdomain-matching rules add a Subdomain column and host_matching rules add a Host column.

<a id="u-665ca6372b4c"></a>
### `dotenv_not_available`

`def dotenv_not_available():` · [tests/test_cli.py:L521-L527][f1]

Returns True only when importing dotenv raises ImportError, otherwise False; it feeds the need_dotenv skipif marker so dotenv-dependent tests are skipped when the package is absent.

<a id="u-b226045b80cd"></a>
### `test_cli_empty`

`def test_cli_empty(app):` · [tests/test_cli.py:L691-L697][f1]

A blueprint with cli_group='blue' but no registered commands must not create an empty group: invoking ['blue', '--help'] through the app's CLI runner exits 2, and the assertion message embeds the unexpected output on failure.

<a id="u-25ddc0f13cfc"></a>
### `test_cli_name`

`def test_cli_name(test_apps):` · [tests/test_cli.py:L41-L45][f1]

Asserts the CLI object exposed by the cliapp test app is a Click command whose name equals the app's name rather than the app object itself, by importing cliapp.app.testapp and comparing testapp.cli.name to testapp.name.

<a id="u-e2852550bd66"></a>
### `test_disable_dotenv_from_env`

`def test_disable_dotenv_from_env(monkeypatch, runner):` · [tests/test_cli.py:L576-L581][f1]

Skipped without dotenv.

Setting FLASK_SKIP_DOTENV=1 and invoking FlaskGroup must suppress dotenv loading entirely: FOO never appears in os.environ despite env files in the working directory.

<a id="u-0d75eab9936f"></a>
### `test_dotenv_optional`

`def test_dotenv_optional(monkeypatch):` · [tests/test_cli.py:L569-L573][f1]

Shadows sys.modules['dotenv'] with None to simulate absence and asserts load_dotenv() is a safe no-op: no FOO appears in os.environ even though test_path contains env files.

<a id="u-b380416fc8d4"></a>
### `test_dotenv_path`

`def test_dotenv_path(monkeypatch):` · [tests/test_cli.py:L559-L566][f1]

Skipped without dotenv.

load_dotenv accepts an explicit path: loading test_path/.flaskenv sets FOO without changing the working directory, and the keys are registered for monkeypatch restoration.

<a id="u-f569c5ce4b97"></a>
### `test_help_echo_loading_error`

`def test_help_echo_loading_error():` · [tests/test_cli.py:L413-L425][f1]

Asking the root flask.cli cli for --help without a loadable app still exits 0: 'FLASK_APP' hint text appears on stderr and 'Usage:' on stdout.

Uses the same CliRunner(mix_stderr=False) construction with a Click >= 8.2 fallback.

**Uncertainties.**

- Behavior of the stderr assertion under the fallback runner is not verified here

<a id="u-9d49d788d69f"></a>
### `test_load_dotenv`

`def test_load_dotenv(monkeypatch): # can't use monkeypatch.delitem since the keys don…` · [tests/test_cli.py:L535-L556][f1]

Skipped without dotenv.

Changes into test_path and asserts load_dotenv() loads both .env and .flaskenv with precedence: values in .env win over .flaskenv (FOO=='env'), single-file values load (BAR=='bar', SPAM=='1'), pre-set environment values are never overwritten (EGGS=='3'), and encoding-aware values load (HAM). load_dotenv on a nonexistent file with load_defaults=False returns False and loads nothing. Environment keys are registered for monkeypatch restoration.

<a id="u-7996659fc3ec"></a>
### `test_locate_app`

`def test_locate_app(test_apps, iname, aname, result):` · [tests/test_cli.py:L180-L196][f1]

Parameterized check of locate_app's name resolution.

cliapp.app resolves to an app named testapp whether or not an attribute name is given. Factory modules resolve through bare names, calls with parentheses, positional string arguments, trailing-comma spacing, and surrounding whitespace; call arguments shape the resulting app name (create_app2("foo", "bar") yields app2_foo_bar). Each case asserts the loaded app's name.

<a id="u-f30bcb155361"></a>
### `test_locate_app_raises`

`def test_locate_app_raises(test_apps, iname, aname):` · [tests/test_cli.py:L199-L219][f1]

Asserts locate_app raises NoAppException for each parameterized failure: nonexistent module names, path-style names, missing app attributes, factories with too few arguments or invalid call syntax, factories returning nothing, nested import errors inside a target module, and non-Python files.

<a id="u-0300613cc136"></a>
### `test_locate_app_suppress_raise`

`def test_locate_app_suppress_raise(test_apps):` · [tests/test_cli.py:L222-L228][f1]

With raise_if_not_found=False, a failure to import the named module returns None instead of raising.

Suppression applies only to the direct import error: cliapp.importerrorapp, whose module body itself fails, still raises NoAppException even with the flag set.

<a id="u-b93bd8b64830"></a>
### `test_no_command_echo_loading_error`

`def test_no_command_echo_loading_error():` · [tests/test_cli.py:L398-L410][f1]

Invoking the root flask.cli cli with an unknown command while no app can be loaded yields exit code 2 with error output containing both the 'FLASK_APP' loading hint and 'Usage:'.

Builds CliRunner(mix_stderr=False) where supported, falling back to a plain CliRunner when that raises DeprecationWarning or TypeError (Click >= 8.2).

**Uncertainties.**

- Whether result.stderr is populated identically under the Click >= 8.2 fallback runner is not verified in this file

<a id="u-8e82959b6aea"></a>
### `test_run_cert_adhoc`

`def test_run_cert_adhoc(monkeypatch):` · [tests/test_cli.py:L602-L616][f1]

Controls the cryptography import via sys.modules monkeypatching.

With cryptography absent, --cert adhoc raises click.BadParameter; with a fake cryptography module present, adhoc is accepted as ctx.params['cert'] verbatim. Supplying --key alongside adhoc still raises BadParameter because adhoc needs no key file.

<a id="u-3aa8d1421b88"></a>
### `test_run_cert_import`

`def test_run_cert_import(monkeypatch):` · [tests/test_cli.py:L619-L638][f1]

Cert values may be import paths to SSLContext objects.

A missing module (not_here) or a module without an SSLContext (flask) raises click.BadParameter. When sys.modules['ssl_context'] holds a real SSLContext, the cert param is that exact object; pairing it with --key raises BadParameter since an SSLContext needs no key.

<a id="u-ae00c9fd8cf0"></a>
### `test_run_cert_no_ssl`

`def test_run_cert_no_ssl(monkeypatch):` · [tests/test_cli.py:L641-L645][f1]

With sys.modules['ssl'] shadowed to None so import fails, resolving an import-style cert value raises click.BadParameter rather than leaking ImportError.

<a id="u-a9566e312500"></a>
### `test_run_cert_path`

`def test_run_cert_path(): # no key` · [tests/test_cli.py:L584-L599][f1]

Exercises run_command's cert/key option coupling.

Passing --cert without --key, or --key without --cert, raises click.BadParameter. When both are given in either order, ctx.params['cert'] becomes the tuple (cert, key), both set to this test file.

<a id="u-bfa4faa1eead"></a>
### `test_run_exclude_patterns`

`def test_run_exclude_patterns():` · [tests/test_cli.py:L700-L702][f1]

Passing --exclude-patterns with this file makes ctx.params['exclude_patterns'] a list containing exactly that argument.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/tests/test_cli.py
