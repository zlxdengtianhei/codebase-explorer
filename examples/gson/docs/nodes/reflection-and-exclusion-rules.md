# Reflection and exclusion rules

**Capability.** Creates reflection-based adapters and applies field and class exclusion policies during binding.

Relevant when reflective object binding or exclusion behavior matters. Reflective support builds adapters and applies naming, accessibility, and reflection filters; exclusion policy configures field and class exclusions.

**Children.**

- [Reflective adapter support](reflective-adapter-support.md) `reflective-adapter-support` · 27 unit(s)
- [Serialization exclusion policy](serialization-exclusion-policy.md) `serialization-exclusion-policy` · 6 unit(s)

**Depends on.**

- [Object construction adapters](object-construction-adapters.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Object construction adapters](object-construction-adapters.md) · graph-confirmed · 7 edge(s)

Parent: [Object binding adapters](object-binding-adapters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
