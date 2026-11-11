# Ruby Greeting and Utilities

**Capability.** Provides a Ruby greeting class, a Util helper module, a lambda-based top function, and a load-time result assignment.

Readers working with the Ruby sample should come here for the greeting class, the Util.helper constant-returning method, and the top function that adds two by default. The file also executes a module-level assignment when loaded.

Parent: [Scripting Language Greeting Demos](scripting-language-greeting-demos.md)

## Units (4)

<a id="u-8384eb4dd77f"></a>
### `sample.rb-greeter-class`

`class Greeter` · [src/sample.rb:L10-L11][f1]

Ruby class whose initialize stores the argument in the @name instance variable; greet returns the interpolated string "hi #{@name}", which raises if greet is called before initialize set @name.

<a id="u-049f856be847"></a>
### `sample.rb-util-module`

`module Util` · [src/sample.rb:L20-L21][f1]

Module defining a singleton method self.helper that returns the constant 1; called as Util.helper.

<a id="u-253924c67d7f"></a>
### `src/sample.rb:top`

`def top(a, b = 1)` · [src/sample.rb:L5-L8][f1]

Defines a lambda inner returning its argument plus one and returns inner.call(a) + b, with b defaulting to 1, so top(a) yields a + 2 by default.

The lambda's call is unresolved in the graph but is standard Ruby.

<a id="u-b5433bc7df9b"></a>
### `sample.rb module code (L24–L26)`

`module_region` · [src/sample.rb:L24-L26][f1]

Module-level statement assigning result = top(1), which evaluates to 4 given the default b of 1; it executes when the file is loaded.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.rb
