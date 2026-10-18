# Rewriting & Explanations

**Capability.** Verifies rewritten assertion explanation messages directly (getmsg/rewrite helpers) including walrus operators, ternary-like comparisons, unbalanced-brace reprs, and leaked walrus state between tests.

Use this subtree for message-level checks of rewriting without full pytester runs. getmsg rewrites and executes a local function's assertions and returns the failure message; issue-specific classes pin regressions.

**Depends on.**

- [Import Hook & Cache Tests](r3-rewrite-hook-tests.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 41 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 37 edge(s)

Parent: [Assertion Rewrite Test Suite](r3-assertrewrite-tests.md)

## Units (8)

<a id="u-a031c2992573"></a>
### `test_assertrewrite.py-test-assertion-rewrite`

`class TestAssertionRewrite:` · [testing/test_assertrewrite.py:L76-L77][f1]

TestAssertionRewrite verifies assertion rewriting and its explanation messages.

Helpers rewrite/getmsg drive in-process checks; pytester-based tests run in-process or subprocess pytest sessions. Key behaviors verified: helper imports are inserted after a docstring or __future__ imports with expected lineno/col_offset across five module layouts (test_place_initial_imports); every rewritten node keeps locations inside the original statement span (test_location_is_set); bytecode instruction positions are identical before and after rewriting for calls, subscripting, unary/binary/comparison operators including reflected and contains forms, star-args and attribute access, in both single-line and multiline operator spellings (test_positions_are_preserved, whose preserved() helper compares dis instruction positions from the loc() frame callback between original and rewritten executions); a module whose first statement is 'PYTEST_DONT_REWRITE' is left unrewritten (test_dont_rewrite), also honored for a plugin under subprocess (test_dont_rewrite_plugin); a plugin package is rewritten (test_rewrites_plugin_as_a_package); PEP 235 same-named modules resolve per sys.path order (test_honors_pep_235). Message tests pin exact explanations: plain and global names render 'assert False'; attribute chains append 'where 3 = x.g'; calls append 'where False = g(...)' including positional, keyword, starred and **dict-unpacked forms; len() appends 'where 10 = len([...])'; chained comparisons report only the failing pair; a custom util._reprcompare hook replaces the explanation; a __bool__ raising ValueError during comparison still yields the custom repr in the message; comma-form messages keep both message and rewritten assert text (bytes messages, '%' left unescaped, evaluated non-string expressions like 1+2 and tuples shown); non-string messages are abbreviated at normal verbosity and shown full under -vv; a __getattr__ raising KeyError still produces the where-chain; multiline and non-ASCII custom reprs are escaped without Unicode errors; an __iter__ raising still gives the comparison explanation; a fixture used without declaring the argument shows the fixture-invocation repr. Boolop tests pin that only the failing sub-expression is shown with 'and'/'or' structure, short-circuit operands are not evaluated (True-or-undefined passes), and call operands gain 'where' lines.

**Uncertainties.**

- Expected strings encode current explainer output; rewriter behavior itself lives in _pytest.assertion.rewrite.

<a id="u-4568048ba717"></a>
### `getmsg`

`def getmsg( f, extra_ns: Mapping[str, object] | None = None, *, must_pass: bool = Fal…` · [testing/test_assertrewrite.py:L49-L73][f1]

Rewrite and execute a local function's assertions, returning its failure message.

It extracts the function's source via _pytest._code, rewrites it, compiles and execs it in a fresh namespace optionally seeded from extra_ns, retrieves the function by name and calls it. If AssertionError is raised: when must_pass is true it calls pytest.fail; otherwise it stringifies the exception, prefixing 'AssertionError: ' only when the message does not already start with 'assert'. If the function does not raise: pytest.fail is called when must_pass is false; otherwise None is returned.

calls: [rewrite](r3-rewrite-core-tests.md#u-8b93dd4369e2); uses: [pytest.fail](../../catalog.json)

**Uncertainties.**

- Source extraction for nested functions relies on _pytest._code; behavior for decorated functions is unverified.

<a id="u-8b93dd4369e2"></a>
### `rewrite`

`def rewrite(src: str) -> ast.Module:` · [testing/test_assertrewrite.py:L43-L46][f1]

Parse a source string into an AST and apply pytest's assertion rewriting in place.

It parses src, calls rewrite_asserts on the parsed Module with the source encoded to bytes, and returns the mutated tree; parsing or rewriting exceptions propagate to the caller.

uses: [rewrite_asserts](../../catalog.json)

**Uncertainties.**

- The AST transformations performed by rewrite_asserts are defined in another module.

<a id="u-b2e8bdb9c4a1"></a>
### `test_assertrewrite.py-test-issue925`

`class TestIssue925:` · [testing/test_assertrewrite.py:L1503-L1504][f1]

TestIssue925 pins ternary-like comparison explanations.

Each test writes a module and asserts the exact rewritten output line: '(False == False) == False' keeps its parentheses, 'False == (False == True) == True' reports as '(False == True) == True', and nested 'True == ((False == True) == True)' is preserved verbatim in the 'E   assert' line.

<a id="u-7f4b34e447a1"></a>
### `test_assertrewrite.py-test-issue10743`

`class TestIssue10743:` · [testing/test_assertrewrite.py:L1555-L1556][f1]

TestIssue10743 covers walrus-operator assertions under rewriting.

Verified behaviors: an assertion whose operand both reads and rebinds a name via 'a := change_value(a)' passes and leaves the rebound value (test_assertion_walrus_operator); 'PYTEST_DONT_REWRITE' modules run unrewritten (test_assertion_walrus_operator_dont_rewrite); inline 'a := a.lower()' works in both operand orders (test_assertion_inline_walrus_operator and _reverse); a walrus to a different name doesn't shadow the compared value and the failure message shows 'assert 'Hello' == 'hello'' (test_assertion_walrus_no_variable_name_conflict); a passing rebinding assertion keeps subsequent asserts seeing the new value (test_assertion_walrus_operator_true_assertion_and_changes_variable_value); a failing rebinding assertion reports the pre-rebinding value (test_assertion_walrus_operator_fail_assertion); boolean composite chains with two walrus rebinds evaluate in order and pass (test_assertion_walrus_operator_boolean_composite); failing boolean composites show the original left operand value in the message, 'assert not (True and False is False)' and 'True and None is None' respectively; and a walrus-rewritten variable does not leak between test functions using the same name (test_assertion_walrus_operator_value_changes_cleared_after_each_test, two tests both passing).

<a id="u-e1a373ee57aa"></a>
### `test_assertrewrite.py-test-issue11028`

`class TestIssue11028:` · [testing/test_assertrewrite.py:L1723-L1724][f1]

TestIssue11028 covers walrus operators in comparison operands where the bound name is reused on the other side.

Verified behaviors: '(obj := "foo") in obj' passes; the bound name passed to json.dumps and compared against its result passes; the name passed positionally, as a keyword argument, and nested inside a function call all pass; and '(obj := 4) > add_one(obj)' fails with 'assert 4 > 5' plus 'where 5 = add_one(4)' in the output.

<a id="u-646ccb52bb1c"></a>
### `test_assertrewrite.py-test-issue11239`

`class TestIssue11239:` · [testing/test_assertrewrite.py:L1810-L1811][f1]

TestIssue11239 is a regression test that walrus-operator rewriting does not leak state between test cases reusing the same variable name.

Two tests run in one module: the first binds 'state' normally, the second binds it via a walrus inside the assert; both pass (ret == 0).

<a id="u-864544d0a929"></a>
### `test_issue731`

`def test_issue731(pytester: Pytester) -> None:` · [testing/test_assertrewrite.py:L1484-L1500][f1]

Regression test that explanation formatting tolerates reprs with unbalanced braces.

It writes a module whose class repr returns a long string containing '{' and '}', asserts on a method call, runs pytest, and asserts the output contains no 'unbalanced braces' line via stdout.no_fnmatch_line.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_assertrewrite.py
