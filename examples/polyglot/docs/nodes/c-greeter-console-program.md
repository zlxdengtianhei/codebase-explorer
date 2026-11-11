# C# Greeter Console Program

**Capability.** Provides a C# Greeter class with greeting and increment operations plus a console Main entry point and helpers.

Readers of the C# sample will find a Greeter class storing a name, a static Main that greets and prints, and small methods for incrementing and greeting. The members form a minimal runnable console program.

Parent: [Polyglot Language Samples Repository](polyglot-language-samples-repository.md)

## Units (4)

<a id="u-49ae493367a6"></a>
### `Sample.cs-greeter-class`

`class Greeter` · [src/Sample.cs:L5-L9][f1]

Greeter stores a name given at construction and offers greeting and increment operations.

Its constructor assigns the string parameter to the private name field; no validation occurs, so null/empty names pass through unchanged.

<a id="u-659a9db40c46"></a>
### `Sample.cs-program-entry-point`

`class Program` · [src/Sample.cs:L27-L29][f1]

Program is a static class whose Main constructs a Greeter with the literal "x", calls Greet, and writes the result to the console via Console.WriteLine; it returns nothing and takes no arguments.

<a id="u-ae1ad1c07ee2"></a>
### `Demo.Greeter.Add`

`public int Add(int a)` · [src/Sample.cs:L19-L19][f1]

Expression-bodied method returning its integer argument plus one.

<a id="u-e4404810c59e"></a>
### `Demo.Greeter.Greet`

`public string Greet()` · [src/Sample.cs:L14-L17][f1]

Returns the string "hi " concatenated with the stored name field.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/Sample.cs
