# Argcomplete tests

**Capability.** Cross-checks pytest's fast file completer against bash compgen using a local FilesCompleter copy and subprocess helpers, skipping on platforms where the comparison is unreliable.

Read this to understand how completer correctness is verified against the reference bash implementation.

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (4)

<a id="u-3123e3d4823d"></a>
### `test_argcomplete-tests`

`def test_compare_with_compgen( self, tmp_path: Path, monkeypatch: MonkeyPatch ) -> None:` · [testing/test_argcomplete.py:L73-L89][f1]

Bash-comparison tests for the fast argcomplete completer, both skipped on win32 and darwin.

test_compare_with_compgen creates a FastFilesCompleter and the reference FilesCompleter, chdirs into tmp_path via monkeypatch, touches a 'data' file after the empty-prefix comparison, and asserts equal_with_bash for the empty prefix and for 'd', 'data', 'doesnotexist', and ''. test_remove_dir_prefix asserts equal_with_bash is False for the prefixed input '/usr/', documented as incompatible with compgen but compatible with bash itself.

calls: [equal_with_bash](r5-argcomplete-tests.md#u-8b1dde8f89a6)

**Uncertainties.**

- tmp_path.cwd() semantics are defined outside this file.

<a id="u-1971919a467c"></a>
### `FilesCompleter`

`class FilesCompleter:` · [testing/test_argcomplete.py:L39-L42][f1]

A file-name completer that shells out to bash compgen, a local copy of argcomplete's FilesCompleter used to cross-check the fast completer (importing argcomplete would open filedescriptor 9 and raise OSError at test end).

__init__ accepts allowednames and directories, wrapping a bare string into a one-element list and stripping leading '*' and '.' from each extension. __call__ has three branches: with allowednames and directories true it first lists directories suffixed with '/', then per extension runs compgen -A file -X '!*.ext'; with allowednames but directories false it skips the directory listing; with no allowednames it lists files via compgen -A file, removes plain directory names from that list (set difference), and re-adds them with a '/' suffix only when directories is true. It returns a list of completion strings.

calls: [_wrapcall](r5-argcomplete-tests.md#u-eb9bda0aab30)

<a id="u-8b1dde8f89a6"></a>
### `equal_with_bash`

`def equal_with_bash(prefix, ffc, fc, out=None):` · [testing/test_argcomplete.py:L15-L24][f1]

Compares a fast file completer's suggestions against bash compgen output for a prefix.

It calls ffc(prefix) for the candidate list, builds a set from fc(prefix), and returns True when set(res) equals the bash set. When the optional out object is supplied it writes a trace line with the result; if the sets differ it additionally writes the python-only and bash-only differences. Duplicates in res do not affect the outcome because equality is set-based.

uses: [FilesCompleter](r5-argcomplete-tests.md#u-1971919a467c)

**Uncertainties.**

- The out parameter's type is not fixed in source; only the duck-typed write call is certain.

<a id="u-eb9bda0aab30"></a>
### `_wrapcall`

`def _wrapcall(*args, **kargs):` · [testing/test_argcomplete.py:L32-L36][f1]

Runs a subprocess and returns its stdout decoded and split into lines.

On subprocess.CalledProcessError it returns []; all other exceptions propagate. Arguments are forwarded unchanged to subprocess.check_output.

**Notes.**

- failure: A nonzero exit status is silently turned into an empty result list.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_argcomplete.py
