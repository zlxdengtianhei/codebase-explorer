# C# Greeter and Shape

**Capability.** Groups C# Greeter, IShape, and Program examples showing constructor name storage, an Area interface, and console greeting output.

Come here for C# class, interface, and entry-point examples. It contains a Greeter with greeting and increment methods, an IShape Area declaration, and a Main that prints a greeting.

Parent: [Cross-Language Object Utilities](cross-language-object-utilities.md)

## Units (3)

<a id="u-28209510c860"></a>
### `Sample.cs-greeter-class-and-methods`

`class Greeter` · [src/Sample.cs:L5-L9][f1]

Greeter stores a name supplied to its constructor and exposes greeting and increment methods.

The constructor assigns the name; Greet returns "hi " concatenated with it; Add returns its integer argument plus one. No validation or exception path is present.

<a id="u-8ab429bfe7b0"></a>
### `Sample.cs-ishape-interface`

`public interface IShape` · [src/Sample.cs:L22-L24][f1]

IShape declares a single Area method returning double.

The interface has no implementation in this file; implementers must supply Area.

<a id="u-659a9db40c46"></a>
### `Sample.cs-program-entry-point`

`class Program` · [src/Sample.cs:L27-L29][f1]

Program is a static class whose Main writes a new Greeter's greeting to the console.

Main constructs Greeter with "x", calls Greet, and passes the result to Console.WriteLine; it returns void and has console output as a side effect.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/src/Sample.cs
