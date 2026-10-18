# Help and Version Output

**Capability.** Registers the informational/debug CLI options, intercepts --help and --version early in cmdline main, prints full help via the terminal reporter, and contributes plugin/version header lines.

Use it to trace how --help/--version exit before a session starts and how header metadata is produced. HelpAction aborts parsing via PrintHelp.

**Depends on.**

- [Built-in Plugins and CLI Facets](r6-builtin-plugins.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r6-helpconfig ` → ` r6-builtin-plugins `)

Parent: [Built-in Plugins and CLI Facets](r6-builtin-plugins.md)

## Units (8)

<a id="u-649bc40e9ab1"></a>
### `helpconfig-pytest-cmdline-parse`

`def unset_tracing() -> None:` · [src/_pytest/helpconfig.py:L132-L136][f1]

Hook wrapper that, when --debug was given, opens the requested file with mode 'w' (truncating it), writes pytest/python versions, invocation dir, cwd and args, then routes pytest's trace output into that file and enables plugin-manager call tracing, notifying the user on stderr.

It registers a cleanup, unset_tracing, that closes the file, restores the trace writer to None, undoes tracing, and reports completion. If --debug is absent the wrapper simply returns the yielded Config unchanged. Inner function unset_tracing is part of this unit.

**Notes.**

- side_effect: The debug log file is opened with 'w' and truncated before any content is written.

calls: [Config.add_cleanup](r2-config-lifecycle.md#u-6ed386e09426)

<a id="u-2504e738c2ba"></a>
### `HelpAction`

`class HelpAction(Action):` · [src/_pytest/helpconfig.py:L19-L29][f1]

An argparse Action for --help that aborts the rest of pytest argument parsing by raising PrintHelp.

__init__ delegates to argparse.Action with nargs=0 and const=True so the option stores a truthy constant without consuming arguments. On __call__ it sets namespace.<dest> to True, then raises PrintHelp only when parser._parser.after_preparse is truthy; if preparse has not finished it records the flag and lets parsing continue, so pytest can act on --help after ini-option resolution without argparse quitting on missing required options.

group: [HelpAction](r6-helpconfig.md#u-2504e738c2ba)

**Uncertainties.**

- behavior depends on the after_preparse attribute being set by the external parser machinery, which is not in this file

<a id="u-c6ed61b1048e"></a>
### `getpluginversioninfo`

`def getpluginversioninfo(config: Config) -> list[str]:` · [src/_pytest/helpconfig.py:L253-L262][f1]

Returns a list of strings describing registered third-party plugins via the plugin manager's list_plugin_distinfo.

If any (plugin, dist) pairs exist, the first line is a header, followed by one indented 'distname-version at location' line per plugin, using the plugin's __file__ or its repr when unavailable. Returns an empty list when no third-party plugins are registered.

<a id="u-e0f2d2c39997"></a>
### `src/_pytest/helpconfig.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/helpconfig.py:L47-L107][f1]

Registers pytest's informational and debugging CLI options in the 'debugconfig' group.

Defines --version/-V as a counting action, --help/-h using HelpAction (via the private _addoption to allow the reserved lowercase short opt), -p/--plugins-like early plugin loading via append with the 'no:' prefix convention, --disable-plugin-autoload, --traceconfig/--trace-config, --debug which takes an optional file name defaulting to pytestdebug.log and is documented to truncate it, and -o/--override-ini as an append option. Purely declarative; options are consumed elsewhere.

<a id="u-d786f4c76abb"></a>
### `src/_pytest/helpconfig.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/helpconfig.py:L156-L165][f1]

Early-exit main logic: if version option is set it prints version info and returns 0; otherwise if help is requested it runs config._do_configure, prints full help, ensures unconfigure, and returns 0.

When neither option is present it returns None so normal command processing proceeds. The 0 return short-circuits the rest of the session.

calls: [Config._do_configure](r2-config-lifecycle.md#u-dd4c3d492d72), [showhelp](r6-helpconfig.md#u-ec19a0f85aba), [showversion](r6-helpconfig.md#u-21b9491b9ea0)

<a id="u-5ea09590318d"></a>
### `src/_pytest/helpconfig.py:pytest_report_header`

`def pytest_report_header(config: Config) -> list[str]:` · [src/_pytest/helpconfig.py:L265-L283][f1]

Produces header lines for the terminal report.

If --debug or --traceconfig was given, adds 'using: pytest-<version>' plus any plugin version lines. Additionally when --traceconfig is active, adds an 'active plugins:' section listing each registered plugin's name and its __file__ (or repr if it has no file). The returned list may be empty when neither option is set.

calls: [getpluginversioninfo](r6-helpconfig.md#u-c6ed61b1048e)

<a id="u-ec19a0f85aba"></a>
### `showhelp`

`def showhelp(config: Config) -> None:` · [src/_pytest/helpconfig.py:L168-L247][f1]

Prints the full help text through the terminal reporter's writer.

It writes the argparse option help, the ini-options header, then iterates registered ini names rendering each as 'name (type):' with wrapped help text; if an ini entry's help is None it raises TypeError. Layout branches on spec length: specs wider than the 24-column indent (minus 3) start help on a new line wrapped to full width; shorter specs pad inline with continuation lines indented. It then lists documented environment variables (CI, BUILD_NUMBER, PYTEST_ADDOPTS, PYTEST_PLUGINS, PYTEST_DISABLE_PLUGIN_AUTOLOAD, PYTEST_DEBUG), pointers to --markers/--fixtures, and finally renders any warning reports collected so far in red.

**Notes.**

- failure: A None help string for any registered ini option raises TypeError from within help rendering.

uses: [HelpAction](r6-helpconfig.md#u-2504e738c2ba)

**Uncertainties.**

- relies on reporter.stats and tw attributes of TerminalReporter not shown here; assertion requires the terminalreporter plugin to be registered

<a id="u-21b9491b9ea0"></a>
### `showversion`

`def showversion(config: Config) -> None:` · [src/_pytest/helpconfig.py:L143-L153][f1]

Implements --version output.

When config.option.version exceeds 1 (i.e. -V given twice) it writes the pytest version and import location to stdout, then appends each line returned by getpluginversioninfo if any plugins were found; with a single -V it writes only a bare 'pytest <version>' line.

calls: [getpluginversioninfo](r6-helpconfig.md#u-c6ed61b1048e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/helpconfig.py
