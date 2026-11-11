# polyglot: code map

This repository is a polyglot collection of small, self-contained code samples spanning PHP, Swift, Ruby, Python, Kotlin, JavaScript, Go, Rust, C, C++, TypeScript, C#, and Java. Its top-level modules divide the work into parallel greeting-and-utility demos for cross-language comparison, parser edge-case fixtures and generics/interface samples for exercising language tooling, and standalone demonstrations of closures, async patterns, structs, workers, and minimal main classes. Each file is intentionally small, mixing reader-facing feature demos with fixture-oriented stress cases.

## Modules

- [**Scripting Language Greeting Demos**](nodes/scripting-language-greeting-demos.md) — Provides matching greeting classes and utility helpers in PHP, Swift, Ruby, Python, and Kotlin for cross-language comparison. (16 units; `sample.rb`, `sample.php`, `sample.py`)
  - [**PHP and Swift Greeting Samples**](nodes/php-and-swift-greeting-samples.md) — Demonstrates the same greeting class and incrementing top function in PHP and Swift for cross-language comparison. (5 units; `sample.php`, `sample.swift`)
  - [**Ruby Greeting and Utilities**](nodes/ruby-greeting-and-utilities.md) — Provides a Ruby greeting class, a Util helper module, a lambda-based top function, and a load-time result assignment. (4 units; `sample.rb`)
  - [**Python Greeting and Math Helpers**](nodes/python-greeting-and-math-helpers.md) — Provides a Python greeting class, a pi-based top function, an identity decorator, and an import-time result assignment. (4 units; `sample.py`)
  - [**Kotlin Greeter and Utilities**](nodes/kotlin-greeter-and-utilities.md) — Provides a Kotlin greeting class, a singleton Util object with a constant helper, and a function adding a list's size. (3 units; `sample.kt`)
- [**Parser Fixtures and Type Samples**](nodes/parser-fixtures-and-type-samples.md) — Supplies parser edge-case files and generic-type examples useful for testing language tooling behavior. (12 units; `sample.cpp`, `sample.ts`, `sample.c`)
  - [**Edge-Case Parsing Fixtures**](nodes/edge-case-parsing-fixtures.md) — Collects C, Python, and SQL files exercising parser edge cases: syntax errors, CRLF, unicode identifiers, and trivial statements. (8 units; `sample.c`, `unicode.py`, `crlf.py`)
  - [**Generics and Interfaces Samples**](nodes/generics-and-interfaces-samples.md) — Shows generic types and functions in C++ and TypeScript, plus a Shape-implementing Circle class. (4 units; `sample.cpp`, `sample.ts`)
- [**JavaScript Closures and Async**](nodes/javascript-closures-and-async.md) — Demonstrates JavaScript closures, async functions, a counter factory, and simple value-passing helpers. (8 units; `js_case.js`, `sample.js`)
- [**Go and Rust Point Samples**](nodes/go-and-rust-point-samples.md) — Provides parallel Go and Rust Point structs with sum methods, plus closure-based top functions and printing entry points. (6 units; `sample.rs`, `sample.go`)
- [**Worker and Queue Case Study**](nodes/worker-and-queue-case-study.md) — Implements a JSON-processing Python worker, a generic TypeScript FIFO job queue with transforms, and a trivial test. (5 units; `python_case.py`, `ts_case.ts`, `test_x.py`)
- [**C# Greeter Console Program**](nodes/c-greeter-console-program.md) — Provides a C# Greeter class with greeting and increment operations plus a console Main entry point and helpers. (4 units; `Sample.cs`)
- [**Java Counter Main Class**](nodes/java-counter-main-class.md) — Provides a Java Main class holding a constructor-set count with add operations and a nested empty-run class. (3 units; `Sample.java`)

## Key flows

- **Python worker helper usage**: The Python worker case study's grouped worker class relies on a helper function to support its processing. — `python_case.py-worker-class` → `helper`
- **C main computes via add**: The C sample's main function calls add to compute its result. — `main` → `add`
- **Python decorated top-level flow**: The Python sample's top-level code, grouped with its inner closure, applies the identity decorator during module execution. — `sample.py module code (L21–L24)` → `sample.py-top-with-inner-closure` → `decorate`
- **Ruby top-level load flow**: The Ruby sample's module-level code invokes the top function when the file is loaded. — `sample.rb module code (L24–L26)` → `src/sample.rb:top`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
