# CLI App Import and Discovery

**Capability.** Imports modules and resolves application objects by name, attribute or factory string, searching a module for the Flask app when unnamed.

Come here to see how the CLI turns an import string into a Flask app. It covers module import, safe parsing of factory calls with ast, app auto-detection and distinguishing call-signature errors.

**Depended on by.**

- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) · model-inferred · 1 inferred relation(s)

Parent: [Flask CLI Implementation](flask-cli-implementation.md)

## Units (4)

<a id="u-cd9b790319da"></a>
### `cli.py-locate-app`

`def locate_app( module_name: str, app_name: str | None, raise_if_not_found: t.Literal…` · [src/flask/cli.py:L229-L232][f1]

Imports a module by name and returns the Flask app in it, either the best guess or the one named by app_name.

The first two definitions are typing overloads; the third is the implementation.
ImportError handling: if the traceback has more than one frame (tb_next set), the error came from inside the imported module, so NoAppException with the formatted traceback is raised regardless of raise_if_not_found. If the module itself was not found, NoAppException('Could not import ...') is raised when raise_if_not_found is True (default), otherwise None is returned. On success, app_name None delegates to find_best_app, else find_app_by_string; their NoAppException propagates. Non-ImportError exceptions during import propagate untouched.

calls: [find_best_app](cli-app-import-and-discovery.md#u-6522d181aa3f), [find_app_by_string](cli-app-import-and-discovery.md#u-81ef5022e21a)

<a id="u-8597d7387a6f"></a>
### `_called_with_wrong_args`

`def _called_with_wrong_args(f: t.Callable[..., Flask]) -> bool:` · [src/flask/cli.py:L94-L117][f1]

Decides whether a TypeError currently being handled came from a bad call signature or from inside the called function, by walking the traceback.

Must be called while the exception is being handled: it reads sys.exc_info()[2]. If any traceback frame's code object is the function's own __code__, the call succeeded and the error came from within the body, so it returns False. If the traceback never reaches the function, the arguments did not bind and it returns True. The local tb is deleted in a finally block to avoid a reference cycle. If called with no active exception, tb is None and it returns True.

<a id="u-81ef5022e21a"></a>
### `find_app_by_string`

`def find_app_by_string(module: ModuleType, app_name: str) -> Flask:` · [src/flask/cli.py:L120-L197][f1]

Resolves an 'attribute' or 'factory(args)' string against a module and returns the resulting Flask app, parsing the string with ast rather than evaluating it.

The string is stripped and parsed as an eval-mode expression; SyntaxError becomes NoAppException. A bare Name gives the attribute name with no arguments. A Call is accepted only if the callee is a simple Name (otherwise NoAppException); positional and keyword arguments are evaluated with ast.literal_eval, skipping **kwargs-style entries (keyword arg None); ValueError from literal parsing becomes a generic NoAppException (note: other literal_eval errors such as TypeError are not caught). Any other expression kind raises NoAppException. The attribute is fetched with getattr (AttributeError becomes NoAppException). If it is a plain function it is called with the parsed args; TypeError is re-raised unchanged when _called_with_wrong_args says the failure was inside the function, else converted to NoAppException. Non-function attributes are used directly, and arguments are ignored in that case. The final object must be a Flask instance or NoAppException is raised.

calls: [_called_with_wrong_args](cli-app-import-and-discovery.md#u-8597d7387a6f)

<a id="u-6522d181aa3f"></a>
### `find_best_app`

`def find_best_app(module: ModuleType) -> Flask:` · [src/flask/cli.py:L41-L91][f1]

Finds a Flask application inside an imported module, trying well-known names, then a single unique instance, then factory functions.

Order: (1) attributes 'app' then 'application' that are Flask instances are returned immediately. (2) All Flask instances in module.__dict__ are collected: exactly one is returned; more than one raises NoAppException asking for 'module:name'. (3) For 'create_app' then 'make_app', if the attribute is a plain function (inspect.isfunction) it is called with no arguments; a Flask result is returned, a non-Flask result falls through to the next name. A TypeError is checked with _called_with_wrong_args: if the call itself failed it becomes NoAppException (chained), otherwise the original TypeError is re-raised. Other exceptions from the factory propagate. (4) If nothing matched, NoAppException says no app or factory was found. Imports Flask lazily from the package to avoid an import cycle.

calls: [_called_with_wrong_args](cli-app-import-and-discovery.md#u-8597d7387a6f)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/pallets/flask/blob/85c5d93cbd049c4bd0679c36fd1ddcae8c37b642/src/flask/cli.py
