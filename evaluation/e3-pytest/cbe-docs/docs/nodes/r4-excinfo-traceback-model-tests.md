# Traceback manipulation tests

**Capability.** The shared h→g→f ValueError chain defined at module level, and the test class exercising Traceback entry access, cutting, filtering, recursion detection, and reprcrash computation over it, with a recursion-limit fixture for fast-failing recursion tests.

These tests define the fixture chain other excinfo tests and even the rerunfailures integration reuse; read here for Traceback data-model semantics.

**Depended on by.**

- [Third-party plugin integration](r4-plugin-integration-tests.md) · graph-confirmed · 1 edge(s)

Parent: [Excinfo and traceback tests](r4-test-excinfo.md)

## Units (3)

<a id="u-051998dfad0e"></a>
### `test_excinfo.py-getstatement-and-chain`

`def test_excinfo_getstatement():` · [testing/code/test_excinfo.py:L77-L78][f1]

Defines the shared raise chain used across the file: module-level f raises ValueError, g calls f with a local __tracebackhide__ = True, h calls g.

test_excinfo_getstatement catches f()→g() and asserts the traceback entry line numbers equal the f/f/g sequence computed from each function's co_firstlineno, pinning entry order and count. The hide flag in g is what later filtering tests rely on to remove exactly that frame.

uses: [test_excinfo.py-traceback-f-g-h](r4-excinfo-traceback-model-tests.md#u-7faf489587bf)

<a id="u-7faf489587bf"></a>
### `test_excinfo.py-traceback-f-g-h`

`class TestTraceback_f_g_h:` · [testing/code/test_excinfo.py:L123-L124][f1]

Test class exercising Traceback entry access, cutting, filtering, recursion detection, and reprcrash computation over the h→g→f ValueError chain captured in setup_method.

setup_method calls h() and stores ExceptionInfo.from_current(); g's frame hides itself, so test_traceback_filter expects filtering to drop exactly one of four raw entries covering f, g, h and pytest internals (flagged as possibly fragile). getsource tests verify entry source text, including a NameError raised at an `except somenoname` line inside a nested xyz(). Cut tests: cut by path+firstlineno or path+lineno keeps one entry; cut(excludepath=pytest's package dir) removes all frames under that directory and leaves the pytester file as last entry's code path. filter_selective parametrizes __tracebackhide__ as callables or errisinstance checks: matching predicates drop two entries (g plus the hide marker in pytest.raises), non-matching drop one. Recursion tests: mutual recursion reports recursionindex() == 3; deleting recursionindex from the class still yields a reprcrash containing the message; reraising the same exception with its traceback yields None; a decorator-double-wrapped call also yields None. getreprcrash tests: with partial hiding, the crash path/lineno point at the first unhidden frame (h, at its raise line); when every frame is hidden, _getreprcrash() returns None.

uses: [test_excinfo.py-getstatement-and-chain](r4-excinfo-traceback-model-tests.md#u-051998dfad0e), [class::Pytester][f2], [class::Traceback][f3]

**Uncertainties.**

- Expected entry count of 4 is commented in the test as possibly fragile, depending on interpreter frame behavior
- The graph shows ambiguous candidate resolution for inner f/g/h calls; each nested helper is lexically local to its test, so cross-test resolution would be a misreading

<a id="u-abfb549ef854"></a>
### `limited_recursion_depth`

`def limited_recursion_depth():` · [testing/code/test_excinfo.py:L38-L43][f1]

Fixture that shrinks the interpreter recursion limit to 150 for the duration of a test and restores the previous limit afterwards, so recursion-error tests fail fast without exhausting the default deep limit.

**Notes.**

- side_effect: Mutates the global recursion limit via sys.setrecursionlimit and restores the prior value at teardown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/code/test_excinfo.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
