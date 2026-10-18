# CBE run status

Run `c84938` · status **running** · updated 2026-10-18T02:00:04Z · review sample · jobs 2 · host api

Semantic review: mode **sample**; 0/1 reviewed by a separate reader of the source. This is independent of the deterministic structure/coverage checks and does not prove whole-map truth.

**Deterministic verification failed** · all_tasks_done, semantic_dispositions_cover_inventory, catalog_navigation_resolves. Inspect `cbe host verify`; fix the cause and rerun verification.

Counts: done 12, leased 2, pending 1

id_corrected 0


index_only_filled 0


| Task | Module | State | Attempts | Seconds | Output | Note |
|---|---|---|---:|---:|---|---|
| names |  | done | 1 | 8.0 | host/accepted/names.json |  |
| module_1 | Core Formatting Header | leased | 5 | 477.0 |  |  |
| module_2 | Formatting Implementation Detail | done | 1 | 291.0 | host/accepted/module_2.json |  |
| module_3 | Core API Header | leased | 5 | 526.0 |  |  |
| module_4 | Date and Time Formatting | done | 1 | 472.0 | host/accepted/module_4.json |  |
| module_5 | Base, ostream, and std types | done | 2 | 272.0 | host/accepted/module_5.json |  |
| module_6 | Dynamic Args and Color Support | done | 2 | 168.0 | host/accepted/module_6.json |  |
| module_7 | C API and Range Formatting | done | 1 | 289.0 | host/accepted/module_7.json |  |
| module_8 | printf and wide-char support | done | 1 | 242.0 | host/accepted/module_8.json |  |
| module_9 | Compile-time and OS-level I/O | done | 1 | 251.0 | host/accepted/module_9.json |  |
| module_10 | Enum Formatting Support | done | 3 | 42.0 | host/accepted/module_10.json |  |
| module_11 | Library Source Implementations | done | 2 | 127.0 | host/accepted/module_11.json |  |
| tree |  | done | 2 | 210.0 | host/accepted/tree.json |  |
| review_1 | Core Formatting Header | pending | 0 |  |  |  |
| system |  | done | 1 | 33.0 | host/accepted/system.json |  |
