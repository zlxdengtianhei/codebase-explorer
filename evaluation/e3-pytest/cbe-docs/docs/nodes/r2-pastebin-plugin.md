# Pastebin Report Plugin

**Capability.** Implements --pastebin: uploads full terminal output or each failed test's report to bpaste.net and prints the resulting URLs.

'all' mode tees output during configure and uploads at unconfigure; 'failed' mode uploads per-failure during terminal summary.

**Depends on.**

- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · model-inferred · 0 edge(s)

Parent: [Terminal I/O & CLI Integration Plugins](r2-io-cli-plugins.md)

## Units (5)

<a id="u-4c47a1375e34"></a>
### `src/_pytest/pastebin.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/pastebin.py:L21-L31][f1]

Register the --pastebin option in the 'terminal reporting' group.

It is a store option with dest 'pastebin', default None, and restricted choices 'failed' and 'all'; anything else is rejected by argparse at parse time.

<a id="u-2c16680b34ee"></a>
### `src/_pytest/pastebin.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/pastebin.py:L34-L46][f1]

For '--pastebin all', tee the entire terminal output into a temp file for later upload.

The hook is marked trylast so it runs after other configure hooks. It acts only when config.option.pastebin == 'all'; it fetches the 'terminalreporter' plugin and, when absent (e.g. on an xdist worker node), does nothing. Otherwise it stores a tempfile.TemporaryFile('w+b') under pastebinfile_key in config.stash (the pastebin file is a UTF-8-encoded binary file) and replaces the terminal writer's write attribute with tee_write, which calls the saved original write and additionally writes the chunk into the stashed file, encoding str input to UTF-8 and passing bytes through unchanged.

**Notes.**

- side_effect: Patching tr._tw.write on the instance mutates the live terminal reporter for the whole session until pytest_unconfigure removes it via del tr._tw.__dict__['write'].

uses: [src/_pytest/pastebin.py:pytest_unconfigure](r2-pastebin-plugin.md#u-331da45449d7)

**Uncertainties.**

- tee_write forwards the return value of the underlying write implicitly by not returning it; whether callers rely on write's return value cannot be determined here.

<a id="u-df2f943e7d26"></a>
### `src/_pytest/pastebin.py:pytest_terminal_summary`

`def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:` · [src/_pytest/pastebin.py:L101-L117][f1]

Upload each failed test's report when '--pastebin failed' is active.

It returns immediately unless terminalreporter.config.option.pastebin == 'failed' and the 'failed' stats category exists. It writes a '='-separated 'Sending information to Paste Service' header, then for each failed report derives the message: from rep.longrepr.reprtraceback.reprentries[-1].reprfileloc, falling back to terminalreporter._getfailureheadline(rep) when that attribute chain raises AttributeError. It renders the full report into a StringIO via a terminal writer built with create_terminal_writer, asserts the rendered text is non-empty, uploads it with create_new_paste, and writes a line '<msg> --> <pastebinurl>'. An upload failure therefore prints the 'bad response:' string as the URL rather than aborting the summary.

calls: [create_new_paste](r2-pastebin-plugin.md#u-d8786a59232d)

**Uncertainties.**

- The assert len(s) would raise AssertionError if a report renders to empty text; no fallback path exists for that case.

<a id="u-331da45449d7"></a>
### `src/_pytest/pastebin.py:pytest_unconfigure`

`def pytest_unconfigure(config: Config) -> None:` · [src/_pytest/pastebin.py:L55-L69][f1]

Finalize the '--pastebin all' flow.

When pastebinfile_key is present in config.stash it seeks the temp file to 0, reads the full session log, closes the file, and deletes the stash entry; it then removes the tee patch by deleting 'write' from the terminal reporter's instance __dict__, restoring the class-level write, writes a '='-separated header 'Sending information to Paste Service', uploads the log via create_new_paste, and prints 'pastebin session-log: <url>'. When the stash key is absent (option not 'all', or no terminal reporter at configure) nothing happens. Upload failures surface as the 'bad response: ...' string returned by create_new_paste rather than an exception, per that function's contract.

calls: [create_new_paste](r2-pastebin-plugin.md#u-d8786a59232d)

**Uncertainties.**

- The graph lists multiple close/read candidates for pastebinfile; the source shows it is always the TemporaryFile stored by pytest_configure, but behavior if that store never happened is guarded only by the stash membership check.

<a id="u-d8786a59232d"></a>
### `create_new_paste`

`def create_new_paste(contents: str | bytes) -> str:` · [src/_pytest/pastebin.py:L72-L98][f1]

Upload contents to the bpaste.net service and return a URL or error text.

It lazily imports re and urllib pieces, POSTs to https://bpa.st with urlencoded params {'code': contents, 'lexer': 'text', 'expiry': '1week'} encoded as ASCII, and decodes the response as UTF-8. On HTTPError it closes the error body via 'with e' (HTTP responses must be closed) and returns 'bad response: <e>'; on any other OSError (e.g. URLError) it returns the same 'bad response:' form without raising. On success it searches the response for href="/raw/(\w+)"; a match yields '<url>/show/<id>', otherwise it returns "bad response: invalid format ('<response>')" with the full response embedded — so all failure modes are reported as returned strings, never exceptions.

**Uncertainties.**

- A non-UTF-8-decodable response body would raise UnicodeDecodeError outside the handled HTTPError/OSError paths; whether urlopen wraps that in an OSError is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pastebin.py
