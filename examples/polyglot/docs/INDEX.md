# polyglot: code map

This repository is a polyglot collection of small code examples and tests. Its top-level modules divide work among cross-language object/utility examples, struct/closure and mixed-syntax cases, JavaScript async/closure patterns, Python worker JSON/state handling, TypeScript shape/identity examples, and queue/trivial tests. The examples emphasize parallel syntax demonstrations rather than a single application; some parser-oriented cases, such as the malformed C file, have explicitly unreliable function boundaries.

## Modules

- [**Cross-Language Object Utilities**](nodes/cross-language-object-utilities.md) — Groups greeter, shape, interface, decorator, and helper examples across Java, Kotlin, Ruby, PHP, Swift, Python, and C#. (24 units; `Sample.cs`, `sample.php`, `sample.swift`)
  - [**Cross-Language Greeter Utilities**](nodes/cross-language-greeter-utilities.md) — Collects Java, Kotlin, and Ruby examples of Greeter, constant Util helpers, and top computations with file-level result assignment. (9 units; `sample.rb`, `Sample.java`, `sample.kt`)
  - [**PHP Swift Shape Examples**](nodes/php-swift-shape-examples.md) — Groups PHP and Swift Greeter, Shape, top-closure, and Swift Point examples that demonstrate parallel class, interface, and closure syntax. (8 units; `sample.php`, `sample.swift`)
  - [**Python Greeter and Decorator**](nodes/python-greeter-and-decorator.md) — Collects Python examples of a greeting class, a top function using math.pi, an identity decorator, and file-level result assignment. (4 units; `sample.py`)
  - [**C# Greeter and Shape**](nodes/c-greeter-and-shape.md) — Groups C# Greeter, IShape, and Program examples showing constructor name storage, an Area interface, and console greeting output. (3 units; `Sample.cs`)
- [**Struct Closure Syntax Examples**](nodes/struct-closure-syntax-examples.md) — Groups struct, closure, arithmetic, template, SQL, and malformed-syntax examples across C, Go, Rust, Python, C++, and related files. (19 units; `sample.rs`, `sample.cpp`, `sample.go`)
  - [**Multi-Language Struct and Closure**](nodes/multi-language-struct-and-closure.md) — Collects C, Go, Rust, and Python examples of structs, point sums, closures, helpers, and simple arithmetic functions. (13 units; `sample.rs`, `sample.go`, `sample.c`)
  - [**Mixed Syntax and Template Examples**](nodes/mixed-syntax-and-template-examples.md) — Groups malformed C, Python wrappers, SQL select, C++ template Box, and maximum examples that exercise parser and syntax handling. (6 units; `sample.cpp`, `crlf.py`, `broken.c`)
- [**JavaScript Async and Closures**](nodes/javascript-async-and-closures.md) — Groups JavaScript examples of async wrappers, closure factories, widgets, async arrows, helper delegation, and arithmetic functions. (6 units; `js_case.js`, `sample.js`)
- [**Worker JSON and State**](nodes/worker-json-and-state.md) — Collects a Python Worker state holder, JSON-processing run method, negative-input helper behavior, and async reset test. (5 units; `python_case.py`)
- [**TypeScript Shape and Identity**](nodes/typescript-shape-and-identity.md) — Groups TypeScript Shape interface, Circle area implementation, and generic identity function examples. (3 units; `sample.ts`)
- [**Queue and Trivial Test**](nodes/queue-and-trivial-test.md) — Groups a generic async FIFO Job queue, a job-payload transform, and a placeholder test asserting only True. (3 units; `ts_case.ts`, `test_x.py`)

## Key flows

- **Worker helper rejection**: The worker run/nested formatter group reaches helper, which handles negative-input rejection. — `python_case.py-worker-run-and-nested-formatter` → `helper`
- **Negative helper test**: The negative-input test exercises helper's rejection behavior. — `test_helper_rejects_negative` → `helper`
- **C add call**: The C sample main uses add for arithmetic. — `main` → `add`
- **Python residual decorator path**: The Python sample residual evaluation enters the top/inner group and decorator example. — `sample.py module code (L21–L24)` → `sample.py-top-and-inner` → `decorate`
- **Ruby top result**: The Ruby sample residual assigns the result of top(1). — `sample.rb module code (L24–L26)` → `src/sample.rb:top`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
