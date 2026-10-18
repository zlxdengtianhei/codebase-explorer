# AssertionRewriter AST Transformation and Runtime Helpers

**Capability.** The AssertionRewriter NodeVisitor rewrites each assert (visit_Assert plus per-expression visitors) into temp-variable assignments and %-format explanation templates, guided by UNARY_MAP/BINOP_MAP constants. Runtime helpers (_call_reprcompare, _call_assertion_pass, _format_*, _saferepr, _get_assertion_exprs) are the API surface the generated code calls at test time.

Read this for how explanations are constructed: push/pop format contexts manage nested placeholders, and helper-emitted calls reach the runtime helpers. rewrite_asserts is the entry point from the import hook.

**Depends on.**

- [Pytest Framework and Test Suite](r8-pytest-root.md) · within containment · 2 edge(s)

**Depended on by.**

- [Rewrite Import Hook and pyc Cache](r8-rewrite-import-hook.md) · graph-confirmed · 1 edge(s)

Parent: [Assertion Rewriting](r8-assertion-rewriting.md)

## Units (35)

<a id="u-b99fa849110b"></a>
### `AssertionRewriter`

`class AssertionRewriter(ast.NodeVisitor):` · [src/_pytest/assertion/rewrite.py:L615-L674][f1]

AST NodeVisitor that rewrites assert statements into equivalent statements that capture intermediate values and raise AssertionError with detailed explanations.

run() locates and replaces each ast.Assert; per-assert state (statements, variables, counters, format-context stack, scope) is reset by visit_Assert, which drives the expression visitors (Name, BoolOp, Compare, Call, etc.) that return rewritten expression nodes plus explanation strings. Walrus reassignments inside asserts are tracked per scope in variables_overwrite so later references display the updated value.

group: [AssertionRewriter.run](r8-assert-rewriter-ast.md#u-445d9db52e7a), [AssertionRewriter.visit_Assert](r8-assert-rewriter-ast.md#u-ae55cb86fdbb)

<a id="u-115d4c38ae91"></a>
### `_call_assertion_pass`

`def _call_assertion_pass(lineno: int, orig: str, expl: str) -> None:` · [src/_pytest/assertion/rewrite.py:L513-L515][f1]

Invokes the registered util._assertion_pass hook with (lineno, original assertion text, explanation) if one exists; otherwise does nothing.

<a id="u-753b83dd68e4"></a>
### `_call_reprcompare`

`def _call_reprcompare( ops: Sequence[str], results: Sequence[bool], expls: Sequence[s…` · [src/_pytest/assertion/rewrite.py:L493-L510][f1]

Runtime helper invoked by rewritten comparisons.

Iterates paired (index, result, explanation); done is computed as 'not res', with any exception during that check treated as done. It stops at the first failed (falsy) comparison. If a custom util._reprcompare hook is registered, it is called with the failing operator and the two compared objects, and a non-None return replaces the built-in explanation; otherwise the recorded explanation string for that index is returned.

<a id="u-3c8776d4cbf6"></a>
### `_check_if_assertion_pass_impl`

`def _check_if_assertion_pass_impl() -> bool:` · [src/_pytest/assertion/rewrite.py:L518-L521][f1]

Returns True only when util._assertion_pass is set, letting rewritten passing assertions skip building explanations when no plugin implements pytest_assertion_pass.

<a id="u-48245ff9806f"></a>
### `_format_assertmsg`

`def _format_assertmsg(obj: object) -> str:` · [src/_pytest/assertion/rewrite.py:L455-L474][f1]

Formats a custom assert message so newlines survive util.format_explanation.

For strings it replaces '\n' with '\n~' and '%' with '%%'. For non-strings it first applies saferepr (with the configured maxsize) and additionally replaces the escaped '\\n' with '\n~', since reprlib escapes newlines in reprs inconsistently. Returns the transformed object as a string-compatible value.

<a id="u-41fd4e6565e5"></a>
### `_format_boolop`

`def _format_boolop(explanations: Iterable[str], is_or: bool) -> str:` · [src/_pytest/assertion/rewrite.py:L488-L490][f1]

Joins operand explanations with ' or ' or ' and ' depending on is_or, wraps in parentheses, and escapes '%' to '%%' for later %-formatting.

<a id="u-0ef32736b9b2"></a>
### `_get_assertion_exprs`

`def _get_assertion_exprs(src: bytes) -> dict[int, str]:` · [src/_pytest/assertion/rewrite.py:L560-L570][f1]

LRU-cached (maxsize=1) tokenizer-based extraction of the source text of each assert expression, returning {lineno: expression string}.

It tokenizes the source bytes, recording the line number when the NAME token 'assert' is seen. It then tracks bracket depth; a depth-0 OP ',' separates expression from message, ending collection: for a same-line assert it trims the last line at the comma offset, for a multi-line assert on the same line it trims at the offset, and for an escaped newline before the message it appends the line prefix. NEWLINE or ENDMARKER also ends collection via _write_and_reset, which stores the joined lines with trailing whitespace and line-continuation backslashes stripped and resets state. Subsequent physical lines of a multi-line assert are appended when not yet seen.

**Uncertainties.**

- Exact interaction with unusual token streams (e.g. asserts inside f-strings) is not derivable from this source alone.

<a id="u-ee65dda7ee6f"></a>
### `_get_maxsize_for_saferepr`

`def _get_maxsize_for_saferepr(config: Config | None) -> int | None:` · [src/_pytest/assertion/rewrite.py:L442-L452][f1]

Derives the saferepr size limit from verbosity: config None or missing means verbosity 0.

verbosity >= 2 returns None (unlimited), verbosity >= 1 returns DEFAULT_REPR_MAX_SIZE * 10, otherwise DEFAULT_REPR_MAX_SIZE.

<a id="u-8bacc7df58bf"></a>
### `_saferepr`

`def _saferepr(obj: object) -> str:` · [src/_pytest/assertion/rewrite.py:L422-L439][f1]

Produces a newline-escaped repr for assertion messages.

For bound methods it returns just the method name, skipping the redundant '<bound method ...>' wrapper. Otherwise it asks _get_maxsize_for_saferepr(util._config) for a size limit: if falsy (None) it uses saferepr_unlimited, else saferepr with that maxsize; newlines are replaced with the literal '\n' escape either way so format_explanation's newline handling is not confused.

calls: [_get_maxsize_for_saferepr](r8-assert-rewriter-ast.md#u-ee65dda7ee6f)

<a id="u-897ec93ad200"></a>
### `_should_repr_global_name`

`def _should_repr_global_name(obj: object) -> bool:` · [src/_pytest/assertion/rewrite.py:L477-L485][f1]

Decides whether a name should be shown by repr in an explanation.

Callable objects only qualify if they are FixtureFunctionDefinition instances (fixtures have more informative reprs than their function name). Non-callables return True when they lack a __name__ attribute; if the hasattr check raises any exception, returns True.

<a id="u-fde49d5e39a6"></a>
### `rewrite_asserts`

`def rewrite_asserts( mod: ast.Module, source: bytes, module_path: str | None = None, …` · [src/_pytest/assertion/rewrite.py:L412-L419][f1]

Entry point that rewrites assert statements in an ast.Module in place by constructing an AssertionRewriter (with module path, config, and source bytes) and calling run(mod).

Returns nothing; the mutation happens on mod.

uses: [AssertionRewriter](r8-assert-rewriter-ast.md#u-b99fa849110b)

<a id="u-6a83642644d9"></a>
### `traverse_node`

`def traverse_node(node: ast.AST) -> Iterator[ast.AST]:` · [src/_pytest/assertion/rewrite.py:L553-L557][f1]

Recursively yields the given AST node and all descendants in depth-first order using ast.iter_child_nodes.

<a id="u-d827273628d7"></a>
### `AssertionRewriter.__init__`

`def __init__( self, module_path: str | None, config: Config | None, source: bytes ) -…` · [src/_pytest/assertion/rewrite.py:L674-L690][f1]

Stores module_path, config, and source bytes; reads the 'enable_assertion_pass_hook' ini when a config is given (False otherwise); initializes scope as an empty tuple and variables_overwrite as a defaultdict(dict) keyed by scope tuples.

<a id="u-52d65d04c09a"></a>
### `AssertionRewriter.assign`

`def assign(self, expr: ast.expr) -> ast.Name:` · [src/_pytest/assertion/rewrite.py:L795-L799][f1]

Emits an assignment of an expression to a fresh temporary variable and returns the variable as a Load-context Name, location-copied from the expression.

<a id="u-270d872ec81a"></a>
### `AssertionRewriter.builtin`

`def builtin(self, name: str) -> ast.Attribute:` · [src/_pytest/assertion/rewrite.py:L811-L814][f1]

Returns an Attribute node referencing a builtin by name through the injected '@py_builtins' alias.

<a id="u-c6176e93de5a"></a>
### `AssertionRewriter.display`

`def display(self, expr: ast.expr) -> ast.expr:` · [src/_pytest/assertion/rewrite.py:L801-L803][f1]

Builds an AST call to this module's _saferepr helper on the given expression, for producing reprs in explanations.

<a id="u-9547b90f327f"></a>
### `AssertionRewriter.explanation_param`

`def explanation_param(self, expr: ast.expr) -> str:` · [src/_pytest/assertion/rewrite.py:L816-L826][f1]

Registers an expression under a fresh '%(pyN)s' placeholder key in the current explanation_specifiers dict and returns the placeholder string for use in explanation templates.

<a id="u-979cea52e769"></a>
### `AssertionRewriter.generic_visit`

`def generic_visit(self, node: ast.AST) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L861-L865][f1]

Default handling for expressions without a dedicated visitor: assigns the node to a temporary variable and returns (variable Name, explanation placeholder of its saferepr).

<a id="u-c4c48ada8467"></a>
### `AssertionRewriter.helper`

`def helper(self, name: str, *args: ast.expr) -> ast.expr:` · [src/_pytest/assertion/rewrite.py:L805-L809][f1]

Builds an AST call to a named helper function on the module-level '@pytest_ar' alias with the supplied argument expressions.

<a id="u-1f576428750d"></a>
### `AssertionRewriter.pop_format_context`

`def pop_format_context(self, expl_expr: ast.expr) -> ast.Name:` · [src/_pytest/assertion/rewrite.py:L841-L859][f1]

Closes the current format context: pops the top placeholder dict, restoring the previous one as current if any.

Builds a Dict node of placeholder keys (as Constants) to their expressions, formats expl_expr % that dict, assigns the result to a fresh '@py_format<N>' variable via an appended statement, records that variable in format_variables when the assertion-pass hook is enabled, and returns the variable as a Load Name.

<a id="u-5a8a490b8271"></a>
### `AssertionRewriter.push_format_context`

`def push_format_context(self) -> None:` · [src/_pytest/assertion/rewrite.py:L828-L839][f1]

Starts a new %-formatting context: creates a fresh explanation_specifiers dict and pushes it onto the stack, so nested explanations can collect their own placeholders.

<a id="u-445d9db52e7a"></a>
### `AssertionRewriter.run`

`def run(self, mod: ast.Module) -> None:` · [src/_pytest/assertion/rewrite.py:L692-L782][f1]

Rewrites all assert statements in an ast.Module.

Returns immediately for an empty module body. It locates the docstring (skipping it and any __future__ imports) and returns without rewriting when the module docstring contains 'PYTEST_DONT_REWRITE'. It then inserts alias imports of builtins as '@py_builtins' and '_pytest.assertion.rewrite' as '@pytest_ar' after the docstring/__future__ block, using the first decorator's line number for decorated functions (issue #4984) and lineno/col_offset keyword arguments on Python >=3.10. Collection walks the module iteratively: function/async-function/class nodes push a scope and a _SCOPE_END_MARKER pops it; list fields have ast.Assert children replaced by self.visit(child) results while other AST children are queued; non-expr single AST fields are also queued (expressions cannot contain asserts and are skipped).

**Notes.**

- contract: The '@py_builtins' and '@pytest_ar' names inserted into the module are relied on by all generated helper calls.

calls: [AssertionRewriter.is_rewrite_disabled](r8-pytest-root.md#u-33f578a38ccd), [AssertionRewriter.visit_Assert](r8-assert-rewriter-ast.md#u-ae55cb86fdbb)

<a id="u-0c34e8b5e1f4"></a>
### `AssertionRewriter.variable`

`def variable(self) -> str:` · [src/_pytest/assertion/rewrite.py:L788-L793][f1]

Allocates a fresh temporary variable name '@py_assert<N>' from variable_counter, appends it to self.variables for later None-ing, and returns the name.

The '@' character cannot appear in Python identifiers, preventing clashes with user names.

<a id="u-ae55cb86fdbb"></a>
### `AssertionRewriter.visit_Assert`

`def visit_Assert(self, assert_: ast.Assert) -> list[ast.stmt]:` · [src/_pytest/assertion/rewrite.py:L867-L986][f1]

Rewrites one assert statement into replacement statements.

First warns (warnings.warn_explicit with PytestAssertRewriteWarning at the assert's line) when the test is a one-element-or-more tuple, the 'always true' parentheses mistake. It resets per-assert state (statements, variables, counter, stack, expl_stmts, format_variables when the hook is enabled) and pushes a format context, then visits the test to get the rewritten condition and explanation string. With enable_assertion_pass_hook, it builds an If(negation) whose fail branch executes expl_stmts and raises AssertionError('_format_assertmsg(msg)' + glue + explanation, formatted via _format_explanation; user messages get '\n>assert ' glue), and whose pass branch calls _check_if_assertion_pass_impl and, if true, runs expl_stmts and _call_assertion_pass with the original source text from _get_assertion_exprs; format variables are cleared to None afterwards. Without the hook, it appends If(negation, expl_stmts) whose body raises AssertionError with 'assert ' or '\n>assert ' prefixed explanation. Finally, all temporary variables are set to None in a trailing Assign, and every generated node lacking a lineno gets the assert's location via ast.copy_location. Returns the replacement statement list.

**Notes.**

- failure: AssertionError is raised by generated code at runtime; a non-empty tuple test additionally emits a compile-time warning, not an error.

calls: [_get_assertion_exprs](r8-assert-rewriter-ast.md#u-0ef32736b9b2); uses: [_format_assertmsg](r8-assert-rewriter-ast.md#u-48245ff9806f), [_call_assertion_pass](r8-assert-rewriter-ast.md#u-115d4c38ae91), [_check_if_assertion_pass_impl](r8-assert-rewriter-ast.md#u-3c8776d4cbf6)

<a id="u-f26d6b7bccf9"></a>
### `AssertionRewriter.visit_Attribute`

`def visit_Attribute(self, attr: ast.Attribute) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L1113-L1123][f1]

Rewrites attribute access.

Non-Load contexts (stores/dels) fall back to generic_visit. For loads, the value is visited, the reconstructed Attribute assigned to a temporary, and the explanation formatted as 'res\n{res = value.attr\n}'.

<a id="u-3572b7c7ba05"></a>
### `AssertionRewriter.visit_BinOp`

`def visit_BinOp(self, binop: ast.BinOp) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L1065-L1073][f1]

Rewrites a binary operation: visits both operands, formats '(left_expl symbol right_expl)' using BINOP_MAP ('%%' for Mod due to string-format escaping), assigns the reconstructed BinOp to a temporary, and returns it with the explanation.

uses: [AssertionRewriter.visit_BinOp](r8-assert-rewriter-ast.md#u-3572b7c7ba05)

<a id="u-889b7999592e"></a>
### `AssertionRewriter.visit_BoolOp`

`def visit_BoolOp(self, boolop: ast.BoolOp) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L1010-L1057][f1]

Rewrites and/or chains with short-circuit-preserving control flow that records each operand's value and explanation.

Each operand's result is assigned to a shared result variable and appended to an expl_list; for operands after the first, an If on the running condition (negated for or) nests the remaining code so later operands only evaluate when the chain continues. When an operand is a Compare over a NamedExpr whose target id was already produced by an earlier operand, the walrus target is renamed to a fresh variable and recorded in variables_overwrite[scope] so later references use the recorded node. Each operand's explanation is formatted in its own pushed format context. Finally _format_boolop joins the collected explanations with ' and '/' or ' and the result variable Name is returned with an explanation placeholder.

uses: [_format_boolop](r8-assert-rewriter-ast.md#u-41fd4e6565e5)

<a id="u-c5499b6f3a8f"></a>
### `AssertionRewriter.visit_Call`

`def visit_Call(self, call: ast.Call) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L1075-L1105][f1]

Rewrites a call expression.

Visits the callee, then each positional argument and keyword value; when an argument is a Name recorded in variables_overwrite[scope] (from a prior walrus rewrite), the recorded node is substituted before visiting. Keywords with a name produce 'name=expl' entries; '**'-style keywords (arg None) produce '**expl'. The new Call is assigned to a temporary and the explanation embeds the assignment: 'res\n{res = f(expls)\n}'.

<a id="u-fafe426a63f0"></a>
### `AssertionRewriter.visit_Compare`

`def visit_Compare(self, comp: ast.Compare) -> tuple[ast.expr, str]:` · [src/_pytest/assertion/rewrite.py:L1125-L1176][f1]

Rewrites comparisons, including chained comparisons, using a per-comparison format context.

If the left side is a Name overwritten by a prior walrus, the recorded node is substituted; a NamedExpr left side is itself recorded in variables_overwrite[scope]. For each operator/comparator pair: if the comparator is a NamedExpr whose target matches the current left result variable, the target is renamed to a fresh variable and recorded; the comparator is visited (parenthesizing nested Compare/BoolOp explanations); a fresh result variable is assigned the two-operand Compare; explanation and operator symbol constants accumulate. At runtime _call_reprcompare is invoked via a helper call with tuples of symbols, result variables, explanations, and objects, allowing custom comparison hooks to override explanations. Multi-operator comparisons combine result variables with an And BoolOp; single ones return the sole variable. Returns the result with an explanation placeholder from the popped format context.

uses: [_call_reprcompare](r8-assert-rewriter-ast.md#u-753b83dd68e4)

<a id="u-ec32f435a662"></a>
### `AssertionRewriter.visit_Name`

`def visit_Name(self, name: ast.Name) -> tuple[ast.Name, str]: # Display the repr of t…` · [src/_pytest/assertion/rewrite.py:L1000-L1008][f1]

Explains a Name: shows its saferepr if it is in locals() at runtime or _should_repr_global_name accepts it, else just the identifier text; returns the node and an explanation placeholder.

uses: [_should_repr_global_name](r8-assert-rewriter-ast.md#u-897ec93ad200)

<a id="u-0906e0a595ad"></a>
### `AssertionRewriter.visit_NamedExpr`

`def visit_NamedExpr(self, name: ast.NamedExpr) -> tuple[ast.NamedExpr, str]: # This m…` · [src/_pytest/assertion/rewrite.py:L988-L998][f1]

Explains a walrus expression: the repr of the target name is shown if the name is in locals() at runtime or _should_repr_global_name accepts it; otherwise the plain name string is shown.

Returns the node unchanged plus an explanation placeholder.

uses: [_should_repr_global_name](r8-assert-rewriter-ast.md#u-897ec93ad200)

<a id="u-915ad4c9257a"></a>
### `AssertionRewriter.visit_Starred`

`def visit_Starred(self, starred: ast.Starred) -> tuple[ast.Starred, str]: # A Starred…` · [src/_pytest/assertion/rewrite.py:L1107-L1111][f1]

Rewrites a starred expression (as in call arguments): visits the inner value and returns a new Starred node with explanation '*' + inner explanation.

<a id="u-c88c321cba79"></a>
### `AssertionRewriter.visit_UnaryOp`

`def visit_UnaryOp(self, unary: ast.UnaryOp) -> tuple[ast.Name, str]:` · [src/_pytest/assertion/rewrite.py:L1059-L1063][f1]

Rewrites a unary operation using the UNARY_MAP format pattern ('not %s', '~%s', '-%s', '+%s'), visiting the operand, assigning the reconstructed UnaryOp to a temporary, and returning pattern % operand explanation.

Unknown unary operators raise KeyError from the map lookup.

<a id="u-d5bd0e3d1e02"></a>
### `rewrite.py module code (L51–L64)`

`module_region` · [src/_pytest/assertion/rewrite.py:L51-L64][f1]

Module tail: the UNARY_MAP and BINOP_MAP operator-to-format-string lookup tables used by the rewriter's unary/binary/comparison visitors; Mod maps to '%%' because the explanations are later %-formatted.

<a id="u-2f9a7fd8f5a0"></a>
### `rewrite.py module code (L521–L552)`

`module_region` · [src/_pytest/assertion/rewrite.py:L521-L552][f1]

Module region between the runtime helper functions and traverse_node/_get_assertion_exprs; contains no named symbols beyond imports/constants per the inventory split.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/rewrite.py
