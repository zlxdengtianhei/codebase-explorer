# Assertion Failure Reporting

**Capability.** Produces human-readable explanations for failed comparisons: type-specialized difference strategies, the assertrepr_compare summary pipeline with pytest's explanation formatting mini-language, and verbosity/CI-aware truncation of long explanations.

Start at assertrepr_compare for the top-level entry; comparison strategies explain specific operand types; truncation limits output to terminal size unless -vv or CI. The module-level hooks (_reprcompare/_assertion_pass) connect the rewriter and protocol to this machinery.

**Children.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) `r2-comparison-strategies` · 9 unit(s)
- [Explanation Summary & Formatting](r2-explanation-formatting.md) `r2-explanation-formatting` · 5 unit(s)
- [Explanation Truncation](r2-explanation-truncation.md) `r2-explanation-truncation` · 4 unit(s)

Parent: [Pytest Codebase](r2-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
