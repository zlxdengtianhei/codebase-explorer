# CBE run status

Run `4138c0` · status **complete** · updated 2026-10-18T06:19:54Z · review sample · jobs 2 · host api

Semantic review: mode **sample**; 1/1 reviewed by a separate reader of the source. This is independent of the deterministic structure/coverage checks and does not prove whole-map truth.

Counts: done 9

id_corrected 2

- module_1: ` src/sample.ts::type_alias::Alias ` → ` src/sample.ts::type_alias::Alias::39 ` (dispositions[src/sample.ts::type_alias::Alias] key)
- module_1: ` src/sample.ts::enum::Color ` → ` src/sample.ts::enum::Color::70 ` (dispositions[src/sample.ts::enum::Color] key)

index_only_filled 1

- module_1: ` src/q.sql::module_residual::::0 ` (missing)

context_fallback 1

- ` src/q.sql `: unsupported_language: no grammar registered for suffix '.sql'; froze one whole-file source chunk; declaration-level detail is unavailable

| Task | Module | State | Attempts | Seconds | Output | Note |
|---|---|---|---:|---:|---|---|
| names |  | done | 1 | 3.0 | host/accepted/names.json |  |
| module_1 | Multi-language sample utilities and greeter fixtures | done | 3 | 108.0 | host/accepted/module_1.json | normalized (45); id_corrected 2; index_only_filled 1 |
| module_2 | Core sample utility tests | done | 1 | 5.0 | host/accepted/module_2.json |  |
| module_3 | JavaScript case-handling sample | done | 1 | 15.0 | host/accepted/module_3.json |  |
| module_4 | Python worker helper with inline test | done | 1 | 25.0 | host/accepted/module_4.json |  |
| module_5 | TypeScript case-handling sample | done | 1 | 15.0 | host/accepted/module_5.json |  |
| tree |  | done | 2 | 30.0 | host/accepted/tree.json |  |
| review_1 | Multi-language sample utilities and greeter fixtures | done | 1 | 13.0 | host/accepted/review_1.json |  |
| system |  | done | 2 | 11.0 | host/accepted/system.json |  |
